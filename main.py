import argparse
import sys
import traceback
from pathlib import Path
from typing import List, Tuple
from playwright.sync_api import sync_playwright

from src.config import AppSettings, ProductProfile, ProductType, PRODUCT_REGISTRY
from src.upscaler import GeminiUpscalerEngine
from src.utils import is_cdp_available, setup_logger


def parse_arguments() -> argparse.Namespace:
    """Configura e analisa os argumentos de linha de comando."""
    parser = argparse.ArgumentParser(
        description="Robô RPA de Upscaling em Lote via Google Gemini Web (Studio Kustom)"
    )
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument(
        "--product", "-p",
        type=str,
        choices=[p.value for p in ProductType],
        help="Tipo de produto a ser processado (ex: POKEMON_CARD, TRADING_CARD, POSTER_A4, etc.)"
    )
    group.add_argument(
        "--all", "-a",
        action="store_true",
        help="Processa todos os perfis de produto sequencialmente"
    )
    group.add_argument(
        "--create-card-template",
        type=str,
        metavar="NOME",
        help="Cria um modelo JSON de ficha técnica de carta Pokémon em data/input/pokemon_card/"
    )
    group.add_argument(
        "--create-opcg-template",
        type=str,
        metavar="NOME",
        help="Cria um modelo JSON de ficha técnica de carta One Piece em data/input/onepiece_card/"
    )
    parser.add_argument(
        "--orientation", "-o",
        type=str,
        choices=["auto", "vertical", "horizontal"],
        default="auto",
        help="Orientação para pôsteres (auto: detecta dimensões da arte; vertical: 210x297/297x420; horizontal: 297x210/420x297)"
    )
    parser.add_argument(
        "--card-style",
        type=str,
        choices=["modern", "classic", "full_art", "standard", "extended", "manga_alt_art"],
        default=None,
        help="Força o estilo visual da carta (Pokémon: modern, classic, full_art | One Piece: standard, extended, manga_alt_art)"
    )
    parser.add_argument(
        "--fit-mode", "-f",
        type=str,
        choices=["pad", "blur_pad", "crop", "stretch", "none"],
        default="pad",
        help="Modo de ajuste às medidas exatas a 300 DPI: pad (preserva 100%% da arte preenchendo margens), blur_pad (fundo desfocado), crop (preenchimento total), stretch (esticar), none (sem calibração)"
    )
    parser.add_argument(
        "--calibrate-existing",
        action="store_true",
        default=False,
        help="Calibra as medidas e 300 DPI das imagens já existentes em data/output/ sem precisar abrir o navegador"
    )
    parser.add_argument(
        "--image", "-i",
        type=str,
        default=None,
        help="Caminho para uma imagem específica a ser processada diretamente (ex: data/input/trading_card/145/back.jpg)"
    )
    parser.add_argument(
        "--card-back",
        type=str,
        metavar="CAMINHO",
        help="Atalho para processar um fundo/verso de carta com sangria de +5mm para cada lado"
    )
    parser.add_argument(
        "--bleed-mm",
        type=float,
        default=5.0,
        help="Margem de sangria em milímetros para cada lado no perfil CARD_BACK (Padrão: 5.0 mm)"
    )
    parser.add_argument(
        "--bleed-only",
        action="store_true",
        default=False,
        help="Aplica a expansão de sangria industrial diretamente sem navegador (ideal para fundos já nítidos)"
    )
    parser.add_argument(
        "--pdf",
        type=str,
        nargs="?",
        const="__ALL__",
        metavar="CAMINHO",
        default=None,
        help="Extrai cada página de PDF como PNG (sem navegador e sem upscaling). Sem valor: processa todos os PDFs de data/input/pdf_extract/"
    )
    parser.add_argument(
        "--pdf-dpi",
        type=int,
        default=300,
        help="DPI de renderização das páginas do PDF (Padrão: 300)"
    )
    parser.add_argument(
        "--pdf-pages",
        type=str,
        default=None,
        help="Páginas a extrair, ex: '1-5,8' (Padrão: todas)"
    )
    parser.add_argument(
        "--pdf-output",
        type=str,
        default=None,
        help="Pasta de saída das páginas (Padrão: data/output/pdf_extract/<nome_do_pdf>/)"
    )
    parser.add_argument(
        "--force", "-F",
        action="store_true",
        default=False,
        help="Força o reprocessamento ignorando arquivos já existentes em output"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=False,
        help="Executa o navegador em modo oculto/headless (Padrão: False para monitoramento visual)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=180000,
        help="Timeout em milissegundos para espera da resposta de cada imagem (Padrão: 180000ms = 3min)"
    )
    return parser.parse_args()


def scan_pending_images(
    profile: ProductProfile,
    settings: AppSettings
) -> Tuple[List[Path], List[Path]]:
    """Varre as pastas de entrada e identifica imagens pendentes versus já processadas (idempotência), incluindo subpastas."""
    input_dir = profile.get_input_dir(settings.data_dir)

    all_files = [
        f for f in input_dir.rglob("*")
        if f.is_file() and f.suffix.lower() in settings.supported_extensions and not f.name.startswith(".")
    ]
    all_files.sort(key=lambda p: str(p.relative_to(input_dir)))

    pending: List[Path] = []
    already_done: List[Path] = []

    for file_path in all_files:
        expected_output = profile.get_target_output_path(file_path, settings.data_dir)
        if expected_output.exists() and expected_output.stat().st_size > 0:
            already_done.append(file_path)
        else:
            pending.append(file_path)

    return pending, already_done


def run_batch_for_profile(
    engine: GeminiUpscalerEngine,
    profile: ProductProfile,
    settings: AppSettings,
    logger,
    orientation: str = "auto",
    card_style: str = None,
    force: bool = False
) -> dict:
    """Executa o lote de processamento para um perfil de produto específico."""
    pending, already_done = scan_pending_images(profile, settings)
    total_found = len(pending) + len(already_done)

    logger.info("=" * 60)
    logger.info(f"Processando Perfil: {profile.display_name} ({profile.product_type.value})")
    logger.info(f"Total encontrado: {total_found} | Já concluídos: {len(already_done)} | Pendentes: {len(pending)}")
    logger.info("=" * 60)

    if not pending and not force:
        logger.info(f"Nenhuma imagem pendente para o perfil '{profile.product_type.value}'.")
        return {"total": total_found, "success": 0, "already_done": len(already_done), "failed": 0}

    files_to_process = (pending + already_done) if force else pending
    success_count = 0
    failed_count = 0

    for idx, image_path in enumerate(files_to_process, start=1):
        rel_name = str(profile.get_relative_input_path(image_path, settings.data_dir))
        logger.info(f"\n[{idx}/{len(files_to_process)}] Processando arquivo: {rel_name}")
        try:
            engine.process_single_image(image_path, profile, orientation=orientation, card_style=card_style, force=force)
            success_count += 1
            logger.info(f"[{idx}/{len(files_to_process)}] ✅ Sucesso: {rel_name}")
        except Exception as e:
            failed_count += 1
            logger.error(f"[{idx}/{len(files_to_process)}] ❌ Erro ao processar '{rel_name}': {str(e)}")
            logger.debug(traceback.format_exc())

    return {
        "total": total_found,
        "success": success_count,
        "already_done": len(already_done),
        "failed": failed_count
    }


def main() -> None:
    """Ponto de entrada principal da CLI de automação."""
    args = parse_arguments()
    settings = AppSettings()
    settings.headless = args.headless
    settings.timeout_ms = args.timeout
    settings.fit_mode = args.fit_mode

    log_file = settings.logs_dir / "automation.log"
    logger = setup_logger(log_file, name="GeminiUpscaler")

    # Extração de páginas de PDF (sem navegador)
    if args.pdf:
        from src.pdf_extractor import PdfPageExtractor
        pdf_dir = settings.data_dir / "input" / "pdf_extract"
        pdf_out_root = settings.data_dir / "output" / "pdf_extract"
        pdf_dir.mkdir(parents=True, exist_ok=True)
        pdf_out_root.mkdir(parents=True, exist_ok=True)

        if args.pdf == "__ALL__":
            pdf_files = sorted(f for f in pdf_dir.glob("*.pdf") if f.is_file())
            if not pdf_files:
                logger.info(f"Nenhum PDF encontrado. Coloque os arquivos .pdf em: {pdf_dir}")
                return
        else:
            candidate = Path(args.pdf)
            if not candidate.exists() and (pdf_dir / candidate.name).exists():
                candidate = pdf_dir / candidate.name
            if not candidate.exists():
                logger.error(f"❌ PDF não encontrado: {args.pdf}")
                sys.exit(1)
            pdf_files = [candidate]

        total_pages = 0
        failed = 0
        for pdf_path in pdf_files:
            out_dir = Path(args.pdf_output) if args.pdf_output else pdf_out_root / pdf_path.stem
            logger.info("=" * 65)
            logger.info(f"📄 Extraindo páginas de '{pdf_path.name}' ({args.pdf_dpi} DPI)")
            logger.info("=" * 65)
            try:
                files = PdfPageExtractor.extract(
                    pdf_path, out_dir, dpi=args.pdf_dpi, pages=args.pdf_pages, force=args.force, logger=logger
                )
                total_pages += len(files)
                logger.info(f"🎉 {len(files)} página(s) em: {out_dir}")
            except Exception as e:
                failed += 1
                logger.error(f"❌ Falha ao extrair '{pdf_path.name}': {e}")
        logger.info(f"\nConcluído: {len(pdf_files) - failed} PDF(s) ok, {failed} falha(s), {total_pages} página(s).")
        if failed:
            sys.exit(1)
        return

    # Criação de template de carta Pokémon
    if args.create_card_template:
        from src.pokemon import PokemonCardManager
        card_dir = PRODUCT_REGISTRY[ProductType.POKEMON_CARD].get_input_dir(settings.data_dir)
        json_path, _ = PokemonCardManager.create_sample_card_file(card_dir, name=args.create_card_template)
        logger.info("=" * 65)
        logger.info(f"✨ Template de Carta Pokémon criado com sucesso!")
        logger.info(f"📄 Arquivo: {json_path}")
        logger.info(f"🖼️ Deposite a arte correspondente com o mesmo nome ({args.create_card_template}.png/.jpg)")
        logger.info(f"   na pasta: {card_dir}")
        logger.info(f"🚀 Para gerar a carta, execute: python main.py -p POKEMON_CARD")
        logger.info("=" * 65)
        return

    # Criação de template de carta One Piece
    if args.create_opcg_template:
        from src.tcg.onepiece import OnePieceCardManager
        op_dir = PRODUCT_REGISTRY[ProductType.ONEPIECE_CARD].get_input_dir(settings.data_dir)
        json_path = OnePieceCardManager.create_template_file(op_dir, name=args.create_opcg_template)
        logger.info("=" * 65)
        logger.info(f"🏴‍☠️ Template de Carta One Piece criado com sucesso!")
        logger.info(f"📄 Arquivo: {json_path}")
        logger.info(f"🖼️ Deposite a arte correspondente com o mesmo nome ({args.create_opcg_template}.png/.jpg)")
        logger.info(f"   na pasta: {op_dir}")
        logger.info(f"🚀 Para gerar a carta, execute: python main.py -p ONEPIECE_CARD")
        logger.info("=" * 65)
        return

    if args.card_back:
        args.image = args.card_back
        args.product = ProductType.CARD_BACK.value

    single_image_path = None
    if args.image:
        single_image_path = Path(args.image)
        if not single_image_path.exists():
            logger.error(f"❌ Imagem especificada não encontrada: {args.image}")
            sys.exit(1)
        if not args.product:
            fname = single_image_path.stem.lower()
            if any(kw in fname for kw in ("back", "verso", "fundo")):
                args.product = ProductType.CARD_BACK.value
            else:
                args.product = ProductType.TRADING_CARD.value

    if not args.all and not args.product and not single_image_path:
        logger.error("❌ Parâmetro ausente: informe --product (-p), --all (-a), --image (-i), --card-back, --create-card-template ou --create-opcg-template.")
        sys.exit(1)

    # Identifica os perfis selecionados
    if args.all:
        selected_profiles = list(PRODUCT_REGISTRY.values())
    else:
        selected_type = ProductType(args.product)
        prof = PRODUCT_REGISTRY[selected_type]
        if selected_type == ProductType.CARD_BACK and args.bleed_mm != 5.0:
            prof.target_dimensions_mm = (63.5 + 2 * args.bleed_mm, 88.9 + 2 * args.bleed_mm)
        selected_profiles = [prof]

    # Modo de calibração direta das imagens já geradas em data/output/
    if args.calibrate_existing:
        logger.info("=" * 65)
        logger.info(f"📐 Modo Calibração Dimensional Ativado (fit_mode: {args.fit_mode})")
        logger.info("=" * 65)
        from src.utils import adjust_image_to_target_dimensions

        calibrated_count = 0
        for prof in selected_profiles:
            out_dir = prof.get_output_dir(settings.data_dir)
            files = [
                f for f in out_dir.rglob("*")
                if f.is_file() and f.suffix.lower() in settings.supported_extensions and not f.name.startswith(".")
            ]
            for f in sorted(files, key=lambda p: str(p)):
                eff_mm = prof.get_effective_dimensions_mm(orientation=args.orientation, image_path=f)
                target_px = prof.get_target_pixel_size(orientation=args.orientation, image_path=f)
                adjust_image_to_target_dimensions(
                    image_path=f,
                    target_dimensions_mm=eff_mm,
                    target_dpi=prof.target_dpi,
                    fit_mode=args.fit_mode,
                    output_path=f
                )
                rel_out = str(f.relative_to(out_dir))
                logger.info(
                    f"✅ Imagem calibrada: {rel_out} -> {target_px[0]}x{target_px[1]}px "
                    f"({eff_mm[0]}x{eff_mm[1]}mm @ {prof.target_dpi} DPI) [{args.fit_mode}]"
                )
                calibrated_count += 1

        logger.info(f"\n🎉 Total de {calibrated_count} imagem(ns) calibrada(s) com sucesso nas medidas exatas!")
        return

    # Modo de sangria industrial direta (sem navegador)
    if args.bleed_only:
        logger.info("=" * 65)
        logger.info(f"🎴 Modo Sangria Direta Ativado (+{args.bleed_mm:.1f}mm cada lado)")
        logger.info("=" * 65)
        from src.card_back import CardBleedEngine

        cb_prof = PRODUCT_REGISTRY[ProductType.CARD_BACK]
        bleed_count = 0
        if single_image_path:
            images_to_bleed = [single_image_path]
        else:
            in_dir = cb_prof.get_input_dir(settings.data_dir)
            images_to_bleed = [
                f for f in in_dir.rglob("*")
                if f.is_file() and f.suffix.lower() in settings.supported_extensions and not f.name.startswith(".")
            ]

        for img_p in images_to_bleed:
            out_p = cb_prof.get_target_output_path(img_p, settings.data_dir)
            CardBleedEngine.apply_bleed(
                image_input=img_p,
                card_dimensions_mm=(63.5, 88.9),
                bleed_mm=args.bleed_mm,
                dpi=cb_prof.target_dpi,
                output_path=out_p,
                generate_proof=True,
            )
            proof_p = out_p.with_name(f"{out_p.stem}_proof.png")
            total_w = 63.5 + 2 * args.bleed_mm
            total_h = 88.9 + 2 * args.bleed_mm
            logger.info(
                f"✅ Sangria aplicada em '{img_p.name}':\n"
                f"   Canvas: {out_p.name} ({total_w:.1f}x{total_h:.1f}mm @ {cb_prof.target_dpi} DPI)\n"
                f"   Prova com corte: {proof_p.name}"
            )
            bleed_count += 1

        logger.info(f"\n🎉 Total de {bleed_count} fundo(s) processado(s) com sangria industrial!")
        return

    # Verificação prévia de pendências
    total_pending_all = 0
    if single_image_path:
        total_pending_all = 1
    else:
        for prof in selected_profiles:
            p_list, _ = scan_pending_images(prof, settings)
            total_pending_all += len(p_list)

    if total_pending_all == 0 and not args.force:
        logger.info("Nenhuma imagem pendente em nenhuma das pastas selecionadas.")
        logger.info("Deposite as imagens a serem aprimoradas dentro de 'data/input/<produto>/' ou utilize --force para reprocessar.")
        return

    summary = {}

    with sync_playwright() as p:
        is_cdp_mode = False

        # Opção 1: Conectar diretamente ao Chrome aberto via CDP (porta 9222, ver iniciar_chrome.bat)
        if is_cdp_available(settings.cdp_url):
            logger.info(f"🔗 Conectando ao Google Chrome já aberto em {settings.cdp_url}...")
            browser = p.chromium.connect_over_cdp(settings.cdp_url)
            context = browser.contexts[0] if browser.contexts else browser.new_context()

            # Procura aba que já contenha o Gemini aberto
            target_page = None
            for p_tab in context.pages:
                if "gemini.google.com" in p_tab.url:
                    target_page = p_tab
                    break

            if not target_page:
                target_page = context.pages[0] if context.pages else context.new_page()
                logger.info(f"Acessando {settings.gemini_url} na aba ativa...")
                target_page.goto(settings.gemini_url, wait_until="domcontentloaded")

            page = target_page
            try:
                page.bring_to_front()
            except Exception:
                pass
            is_cdp_mode = True
        else:
            # Opção 2: Iniciar Google Chrome com contexto persistente (perfil isolado em data/browser_profile)
            temp_dl_dir = settings.data_dir / "temp_downloads"
            temp_dl_dir.mkdir(parents=True, exist_ok=True)

            logger.info(f"Iniciando Google Chrome com perfil isolado em: {settings.user_data_dir.resolve()}")
            try:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=str(settings.user_data_dir.resolve()),
                    channel="chrome",
                    headless=settings.headless,
                    accept_downloads=True,
                    downloads_path=str(temp_dl_dir.resolve()),
                    args=[
                        "--start-maximized",
                        "--disable-blink-features=AutomationControlled"
                    ],
                    no_viewport=True,
                )
            except Exception as e:
                logger.warning(f"Chrome nativo indisponível ({e}). Usando Chromium padrão...")
                context = p.chromium.launch_persistent_context(
                    user_data_dir=str(settings.user_data_dir.resolve()),
                    headless=settings.headless,
                    accept_downloads=True,
                    downloads_path=str(temp_dl_dir.resolve()),
                    args=[
                        "--start-maximized",
                        "--disable-blink-features=AutomationControlled"
                    ],
                    no_viewport=True,
                )
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(settings.gemini_url, wait_until="domcontentloaded")
            try:
                page.bring_to_front()
            except Exception:
                pass

        engine = GeminiUpscalerEngine(context=context, page=page, settings=settings, logger=logger)

        try:
            if single_image_path:
                prof = selected_profiles[0]
                logger.info("=" * 60)
                logger.info(f"Processando Imagem Individual: {single_image_path.name}")
                logger.info(f"Perfil: {prof.display_name} ({prof.product_type.value})")
                logger.info("=" * 60)
                try:
                    engine.process_single_image(
                        single_image_path,
                        prof,
                        orientation=args.orientation,
                        card_style=args.card_style,
                        force=args.force
                    )
                    summary[prof.product_type.value] = {"total": 1, "success": 1, "already_done": 0, "failed": 0}
                except Exception as e:
                    logger.error(f"❌ Erro ao processar '{single_image_path.name}': {str(e)}")
                    logger.debug(traceback.format_exc())
                    summary[prof.product_type.value] = {"total": 1, "success": 0, "already_done": 0, "failed": 1}
            else:
                for prof in selected_profiles:
                    stats = run_batch_for_profile(
                        engine, prof, settings, logger, orientation=args.orientation, card_style=args.card_style, force=args.force
                    )
                    summary[prof.product_type.value] = stats
        finally:
            if not is_cdp_mode:
                logger.info("Fechando contexto do navegador com segurança...")
                context.close()
            else:
                logger.info("Desconectando da sessão remota do Chrome...")

    # Relatório Final Consolidado
    logger.info("\n" + "=" * 65)
    logger.info("                RELATÓRIO FINAL DO LOTE")
    logger.info("=" * 65)
    for prod_key, res in summary.items():
        logger.info(
            f"• {prod_key:<15}: Total: {res['total']} | Sucesso: {res['success']} | "
            f"Existentes: {res['already_done']} | Falhas: {res['failed']}"
        )
    logger.info("=" * 65)
    logger.info("Processamento finalizado. Verifique a pasta 'data/output/' para ver os resultados.")


if __name__ == "__main__":
    main()
