import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

from src.config import AppSettings
from src.utils import is_cdp_available, setup_logger


def initialize_browser_session() -> None:
    """Inicia o Google Chrome com perfil persistente isolado para o usuário realizar login no Google Gemini."""
    settings = AppSettings()
    log_file = settings.logs_dir / "init_session.log"
    logger = setup_logger(log_file, name="InitSession")

    logger.info("=====================================================")
    logger.info("  INICIALIZAÇÃO DE SESSÃO PERSISTENTE - GOOGLE GEMINI")
    logger.info("=====================================================")

    # 1. Verifica se o Chrome com CDP já está em execução
    if is_cdp_available(settings.cdp_url):
        logger.info(f"✅ Google Chrome detectado já rodando na porta 9222 ({settings.cdp_url})!")
        logger.info("A automação se conectará diretamente à sessão atual do Chrome de automação.")
        logger.info("Você já pode executar 'python main.py' diretamente.")
        return

    with sync_playwright() as p:
        logger.info(f"Usando Google Chrome com perfil isolado em: {settings.user_data_dir.resolve()}")
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(settings.user_data_dir.resolve()),
                channel="chrome",
                headless=False,
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
                headless=False,
                args=[
                    "--start-maximized",
                    "--disable-blink-features=AutomationControlled"
                ],
                no_viewport=True,
            )

        page = context.pages[0] if context.pages else context.new_page()
        logger.info(f"Acessando {settings.gemini_url}...")
        page.goto(settings.gemini_url)

        print("\n" + "=" * 65)
        print(" [ATENÇÃO] Faça login na sua conta Google no navegador aberto.")
        print(" Se já estiver logado ou quando a tela inicial do Gemini carregar:")
        print(" 👉 Pressione [ENTER] AQUI NO TERMINAL para salvar a sessão.")
        print("=" * 65 + "\n")

        try:
            input("Pressione ENTER após concluir o login no navegador...")
        except KeyboardInterrupt:
            logger.info("Cancelado pelo usuário.")
        finally:
            logger.info("Salvando estado da sessão e fechando o navegador...")
            context.close()
            logger.info("Sessão persistida com sucesso em data/browser_profile/!")
            logger.info("Você já pode executar 'python main.py' para processar imagens.")


if __name__ == "__main__":
    initialize_browser_session()
