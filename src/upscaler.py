import base64
import logging
import time
from pathlib import Path
from typing import Optional

from playwright.sync_api import BrowserContext, Page, TimeoutError as PlaywrightTimeoutError

from src.config import AppSettings, ProductProfile
from src.selectors import GeminiSelectors
from src.utils import copy_image_to_clipboard


class GeminiUpscalerEngine:
    """Motor de automação Playwright para interação com a interface Web do Google Gemini."""

    def __init__(
        self,
        context: BrowserContext,
        page: Page,
        settings: AppSettings,
        logger: Optional[logging.Logger] = None
    ) -> None:
        self.context = context
        self.page = page
        self.settings = settings
        self.logger = logger or logging.getLogger("GeminiUpscaler")

    def dismiss_modals_if_present(self) -> None:
        """Fecha modais ou diálogos de consentimento/novidades que possam obstruir a UI."""
        try:
            dismiss_buttons = self.page.locator(GeminiSelectors.MODAL_DISMISS_BUTTON)
            count = dismiss_buttons.count()
            if count > 0:
                for i in range(count):
                    btn = dismiss_buttons.nth(i)
                    if btn.is_visible():
                        self.logger.info("Fechando modal/diálogo informativo...")
                        btn.click(timeout=1500)
                        self.page.wait_for_timeout(500)
        except Exception:
            pass

    def ensure_chat_ready(self) -> None:
        """Garante que a página está aberta no Gemini e inicia um novo chat para limpar o histórico."""
        gemini_tab = None
        for p in self.context.pages:
            if "gemini.google.com" in p.url:
                gemini_tab = p
                break

        if gemini_tab:
            self.page = gemini_tab
            try:
                self.page.bring_to_front()
            except Exception:
                pass
        else:
            current_url = self.page.url
            if "gemini.google.com" not in current_url:
                self.logger.info(f"Navegando para {self.settings.gemini_url}...")
                try:
                    self.page.goto(self.settings.gemini_url, wait_until="domcontentloaded", timeout=30000)
                    self.page.bring_to_front()
                except Exception as e:
                    self.logger.warning(f"Aviso na navegação inicial ({e}), prosseguindo...")

        self.dismiss_modals_if_present()

        # Verifica se caiu em tela de login
        if "accounts.google.com" in self.page.url or "signin" in self.page.url:
            self.logger.error("⚠️ O navegador está na tela de login do Google!")
            self.logger.error("DICA: Feche o Brave, execute 'iniciar_brave.bat' e depois 'python main.py --all'.")

        # Clica no botão de Novo Chat para isolar o contexto de cada imagem
        try:
            new_chat = self.page.locator(GeminiSelectors.NEW_CHAT_BUTTON).first
            if new_chat.is_visible():
                self.logger.debug("Iniciando novo chat para isolamento de contexto...")
                new_chat.click(timeout=3000)
                self.page.wait_for_timeout(1000)
        except Exception as e:
            self.logger.debug(f"Não foi necessário clicar em Novo Chat ou botão indisponível: {e}")

        # Aguarda a caixa de prompt estar visível
        try:
            self.page.wait_for_selector(GeminiSelectors.PROMPT_INPUT, state="visible", timeout=15000)
        except Exception as e:
            self.logger.warning(f"Aguardando caixa de prompt: {e}")

    def _upload_image(self, image_path: Path) -> None:
        """Realiza o upload da imagem colando via Clipboard (Ctrl+C / Ctrl+V) na caixa de prompt."""
        self.logger.info(f"📋 Copiando imagem para a área de transferência: {image_path.name}")
        abs_path = str(image_path.resolve())

        # Garante foco na caixa de texto do prompt
        prompt_box = self.page.locator(GeminiSelectors.PROMPT_INPUT).first
        prompt_box.click()
        self.page.wait_for_timeout(500)

        # 1. Copia a imagem para o Clipboard do Windows
        copied = copy_image_to_clipboard(image_path)
        if copied:
            self.logger.info("📌 Colando imagem no Gemini com Ctrl+V...")
            self.page.keyboard.press("Control+v")
            # Aguarda a miniatura da imagem aparecer na caixa de entrada
            self.page.wait_for_timeout(3500)
            self.logger.info("✅ Imagem colada com sucesso via Ctrl+V.")
            return

        # 2. Fallback: Se o clipboard falhar, tenta via seletor de arquivo do DOM
        self.logger.warning("Falha ao copiar via clipboard, tentando via input de arquivo...")
        try:
            file_inputs = self.page.locator(GeminiSelectors.FILE_INPUT)
            if file_inputs.count() > 0:
                file_inputs.first.set_input_files(abs_path)
                self.page.wait_for_timeout(2500)
                return
        except Exception as e:
            self.logger.debug(f"Fallback de arquivo falhou: {e}")

        raise RuntimeError(f"Não foi possível colar ou enviar a imagem '{image_path.name}'")

    def _inject_prompt_and_send(self, prompt_text: str) -> None:
        """Digita o prompt técnico especializado mantendo a imagem anexada e envia a mensagem."""
        self.logger.info("Injetando prompt especializado no editor...")
        prompt_box = self.page.locator(GeminiSelectors.PROMPT_INPUT).first
        prompt_box.click()
        self.page.wait_for_timeout(300)

        # Digita o texto sequencialmente para não sobrescrever o anexo colado
        self.page.keyboard.type(prompt_text, delay=5)
        self.page.wait_for_timeout(1000)

        # Envia a mensagem
        send_btn = self.page.locator(GeminiSelectors.SEND_BUTTON).first
        if send_btn.is_visible() and send_btn.is_enabled():
            send_btn.click()
        else:
            prompt_box.press("Enter")

        self.logger.info("Prompt enviado com sucesso. Aguardando geração da IA...")

    def _extract_generated_model_image(self) -> Optional[bytes]:
        """Extrai exclusivamente a imagem gerada na RESPOSTA DO MODELO (ignorando a imagem enviada pelo usuário)."""
        try:
            data_url = self.page.evaluate("""
                async () => {
                    // 1. Procura blocos de resposta do modelo (model-response)
                    const modelResponses = Array.from(
                        document.querySelectorAll('model-response, .model-response, [data-test-id="model-response"], .response-container')
                    );
                    
                    let targetImg = null;
                    if (modelResponses.length > 0) {
                        const lastResponse = modelResponses[modelResponses.length - 1];
                        const imgs = Array.from(lastResponse.querySelectorAll('img')).filter(img => {
                            const w = img.naturalWidth || img.clientWidth || 0;
                            const h = img.naturalHeight || img.clientHeight || 0;
                            return (w > 150 || h > 150) && !img.src.includes('avatar') && !img.src.includes('profile');
                        });
                        if (imgs.length > 0) {
                            targetImg = imgs[imgs.length - 1];
                        }
                    }

                    // 2. Fallback: imagens fora da área de prompt e fora de user-query
                    if (!targetImg) {
                        const allImgs = Array.from(document.querySelectorAll('img')).filter(img => {
                            const inUserArea = img.closest('user-query, .user-query, rich-textarea, .attachment-container, .input-area');
                            const w = img.naturalWidth || img.clientWidth || 0;
                            const h = img.naturalHeight || img.clientHeight || 0;
                            return !inUserArea && (w > 200 || h > 200) && !img.src.includes('avatar') && !img.src.includes('profile');
                        });
                        if (allImgs.length > 0) {
                            targetImg = allImgs[allImgs.length - 1];
                        }
                    }

                    if (!targetImg) return null;

                    // 3. Extrai bytes da imagem
                    try {
                        const res = await fetch(targetImg.src);
                        const blob = await res.blob();
                        return new Promise((resolve) => {
                            const reader = new FileReader();
                            reader.onloadend = () => resolve(reader.result);
                            reader.readAsDataURL(blob);
                        });
                    } catch (e) {
                        try {
                            const canvas = document.createElement('canvas');
                            canvas.width = targetImg.naturalWidth || targetImg.clientWidth || 1024;
                            canvas.height = targetImg.naturalHeight || targetImg.clientHeight || 1024;
                            const ctx = canvas.getContext('2d');
                            ctx.drawImage(targetImg, 0, 0);
                            return canvas.toDataURL('image/png');
                        } catch (err) {
                            return null;
                        }
                    }
                }
            """)
            if data_url and "," in data_url:
                _, encoded = data_url.split(",", 1)
                img_bytes = base64.b64decode(encoded)
                if len(img_bytes) > 2000:
                    return img_bytes
        except Exception as e:
            self.logger.debug(f"Extração JS da imagem do modelo falhou: {e}")
        return None

    def _wait_and_download_result(self, target_output_path: Path) -> Path:
        """Aguarda a conclusão total do processamento da IA e salva a imagem gerada."""
        start_time = time.time()
        timeout_sec = self.settings.timeout_ms / 1000.0

        self.logger.info("Aguardando IA processar e gerar a nova imagem de alta resolução...")
        
        # Espera inicial para início da geração
        time.sleep(5.0)

        # 1. Aguarda o término dos indicadores de carregamento/geração
        while (time.time() - start_time) < timeout_sec:
            # Verifica se o botão "Parar resposta" (stop button) ou barra de progresso ainda estão ativos
            generating = self.page.locator(
                "button[aria-label*='Stop' i], button[aria-label*='Interromper' i], mat-progress-bar, div.sparkle-container"
            )
            is_still_generating = False
            for i in range(generating.count()):
                try:
                    if generating.nth(i).is_visible():
                        is_still_generating = True
                        break
                except Exception:
                    pass

            # 2. Tenta encontrar a imagem especificamente dentro da resposta do modelo
            raw_bytes = self._extract_generated_model_image()
            if raw_bytes and not is_still_generating:
                target_output_path.write_bytes(raw_bytes)
                self.logger.info(
                    f"✅ Imagem gerada salva com sucesso ({len(raw_bytes) / 1024:.1f} KB) em: {target_output_path.name}"
                )
                return target_output_path

            # 3. Tentativa via botão de download do card gerado
            model_cards = self.page.locator("model-response, .model-response, [data-test-id='model-response']")
            if model_cards.count() > 0 and not is_still_generating:
                last_card = model_cards.last
                download_btn = last_card.locator(
                    "button[aria-label*='download' i], button[aria-label*='baixar' i], button[aria-label*='tamanho original' i], button:has(mat-icon:has-text('download'))"
                ).first
                if download_btn.is_visible():
                    try:
                        self.logger.info("Acionando botão de download nativo do card gerado...")
                        with self.page.expect_download(timeout=10000) as download_info:
                            download_btn.click()
                        download = download_info.value
                        download.save_as(str(target_output_path.resolve()))
                        self.logger.info(f"✅ Download nativo concluído: {target_output_path.name}")
                        return target_output_path
                    except Exception as e:
                        self.logger.debug(f"Download nativo via evento falhou ({e}), aguardando extração...")

            self.page.wait_for_timeout(2500)

        raise PlaywrightTimeoutError(
            f"Tempo limite excedido ({timeout_sec:.0f}s) aguardando a imagem gerada pelo Gemini."
        )

    def process_single_image(self, image_path: Path, profile: ProductProfile) -> Path:
        """Executa o pipeline completo de upscaling para um único arquivo de imagem."""
        output_dir = profile.get_output_dir(self.settings.data_dir)
        target_output_path = output_dir / f"{image_path.stem}{profile.output_suffix}.png"

        # Idempotência: Ignora se já existir
        if target_output_path.exists() and target_output_path.stat().st_size > 0:
            self.logger.info(f"[IDEMPOTÊNCIA] Arquivo já processado anteriormente: {target_output_path.name}")
            return target_output_path

        self.logger.info(f"=== Iniciando Upscaling para '{image_path.name}' | Perfil: {profile.display_name} ===")

        # 1. Prepara novo chat
        self.ensure_chat_ready()

        # 2. Faz upload da imagem colando via Ctrl+V
        self._upload_image(image_path)

        # 3. Digita o prompt técnico e dispara o envio
        self._inject_prompt_and_send(profile.system_prompt)

        # 4. Aguarda e baixa o resultado gerado
        saved_path = self._wait_and_download_result(target_output_path)

        # 5. Delay configurado entre arquivos para respeito de taxa
        time.sleep(self.settings.delay_between_files_sec)

        return saved_path
