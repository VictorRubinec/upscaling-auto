import argparse
import sys
import traceback
from pathlib import Path
from typing import List, Tuple
from playwright.sync_api import sync_playwright

from src.config import AppSettings, ProductProfile, ProductType, PRODUCT_REGISTRY, find_brave_executable
from src.upscaler import GeminiUpscalerEngine
from src.utils import is_cdp_available, setup_logger


def parse_arguments() -> argparse.Namespace:
    """Configura e analisa os argumentos de linha de comando."""
    parser = argparse.ArgumentParser(
        description="Robô RPA de Upscaling em Lote via Google Gemini Web (Studio Kustom)"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--product", "-p",
        type=str,
        choices=[p.value for p in ProductType],
        help="Tipo de produto a ser processado (ex: POSTER_A4, MUG, etc.)"
    )
    group.add_argument(
        "--all", "-a",
        action="store_true",
        help="Processa todos os perfis de produto sequencialmente"
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
    """Varre as pastas de entrada e identifica imagens pendentes versus já processadas (idempotência)."""
    input_dir = profile.get_input_dir(settings.data_dir)
    output_dir = profile.get_output_dir(settings.data_dir)

    all_files = [
        f for f in input_dir.iterdir()
        if f.is_file() and f.suffix.lower() in settings.supported_extensions
    ]

    pending: List[Path] = []
    already_done: List[Path] = []

    for file_path in all_files:
        expected_output = output_dir / f"{file_path.stem}{profile.output_suffix}.png"
        if expected_output.exists() and expected_output.stat().st_size > 0:
            already_done.append(file_path)
        else:
            pending.append(file_path)

    return pending, already_done


def run_batch_for_profile(
    engine: GeminiUpscalerEngine,
    profile: ProductProfile,
    settings: AppSettings,
    logger
) -> dict:
    """Executa o lote de processamento para um perfil de produto específico."""
    pending, already_done = scan_pending_images(profile, settings)
    total_found = len(pending) + len(already_done)

    logger.info("=" * 60)
    logger.info(f"Processando Perfil: {profile.display_name} ({profile.product_type.value})")
    logger.info(f"Total encontrado: {total_found} | Já concluídos: {len(already_done)} | Pendentes: {len(pending)}")
    logger.info("=" * 60)

    if not pending:
        logger.info(f"Nenhuma imagem pendente para o perfil '{profile.product_type.value}'.")
        return {"total": total_found, "success": 0, "already_done": len(already_done), "failed": 0}

    success_count = 0
    failed_count = 0

    for idx, image_path in enumerate(pending, start=1):
        logger.info(f"\n[{idx}/{len(pending)}] Processando arquivo: {image_path.name}")
        try:
            engine.process_single_image(image_path, profile)
            success_count += 1
            logger.info(f"[{idx}/{len(pending)}] ✅ Sucesso: {image_path.name}")
        except Exception as e:
            failed_count += 1
            logger.error(f"[{idx}/{len(pending)}] ❌ Erro ao processar '{image_path.name}': {str(e)}")
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

    log_file = settings.logs_dir / "automation.log"
    logger = setup_logger(log_file, name="GeminiUpscaler")

    # Identifica os perfis selecionados
    if args.all:
        selected_profiles = list(PRODUCT_REGISTRY.values())
    else:
        selected_type = ProductType(args.product)
        selected_profiles = [PRODUCT_REGISTRY[selected_type]]

    # Verificação prévia de pendências
    total_pending_all = 0
    for prof in selected_profiles:
        p_list, _ = scan_pending_images(prof, settings)
        total_pending_all += len(p_list)

    if total_pending_all == 0:
        logger.info("Nenhuma imagem pendente em nenhuma das pastas selecionadas.")
        logger.info(f"Deposite as imagens a serem aprimoradas dentro de 'data/input/<produto>/' e execute novamente.")
        return

    summary = {}
    brave_exe = find_brave_executable()

    with sync_playwright() as p:
        is_cdp_mode = False

        # Opção 1: Conectar diretamente ao Brave aberto via CDP (porta 9222)
        if is_cdp_available(settings.cdp_url):
            logger.info(f"🔗 Conectando ao Brave Browser já aberto em {settings.cdp_url}...")
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
            # Opção 2: Iniciar Brave com contexto persistente
            if brave_exe:
                logger.info(f"Iniciando Brave Browser: {brave_exe}")
                context = p.chromium.launch_persistent_context(
                    user_data_dir=str(settings.user_data_dir.resolve()),
                    executable_path=str(brave_exe),
                    headless=settings.headless,
                    args=[
                        "--start-maximized",
                        "--disable-blink-features=AutomationControlled"
                    ],
                    no_viewport=True,
                )
            else:
                logger.info(f"Iniciando Chrome persistente em: {settings.user_data_dir.resolve()}")
                try:
                    context = p.chromium.launch_persistent_context(
                        user_data_dir=str(settings.user_data_dir.resolve()),
                        channel="chrome",
                        headless=settings.headless,
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
            for prof in selected_profiles:
                stats = run_batch_for_profile(engine, prof, settings, logger)
                summary[prof.product_type.value] = stats
        finally:
            if not is_cdp_mode:
                logger.info("Fechando contexto do navegador com segurança...")
                context.close()
            else:
                logger.info("Desconectando da sessão remota do Brave...")

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
