import base64
import logging
import time
from pathlib import Path
from typing import Optional

from playwright.sync_api import BrowserContext, Page, TimeoutError as PlaywrightTimeoutError

from src.config import AppSettings, ProductProfile, ProductType
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
        try:
            for p in self.context.pages:
                if not p.is_closed() and "gemini.google.com" in p.url:
                    gemini_tab = p
                    break
        except Exception:
            pass

        if gemini_tab:
            self.page = gemini_tab
            try:
                self.page.bring_to_front()
            except Exception:
                pass
        else:
            try:
                if self.page.is_closed():
                    self.page = self.context.new_page()
                current_url = self.page.url
            except Exception:
                self.page = self.context.new_page()
                current_url = ""

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
            self.logger.error("DICA: Execute 'python init_session.py' para logar no Google no perfil de automação (ou 'iniciar_chrome.bat') e depois 'python main.py --all'.")

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
            self.page.wait_for_timeout(1000)
        except Exception as e:
            self.logger.warning(f"Aguardando caixa de prompt: {e}")

    def _is_attachment_present(self) -> bool:
        """Verifica se há uma imagem/anexo presente no campo de prompt antes do envio."""
        try:
            # 1. Verifica via locator do Playwright
            loc = self.page.locator(GeminiSelectors.ATTACHMENT_PREVIEW)
            if loc.count() > 0:
                for i in range(loc.count()):
                    try:
                        if loc.nth(i).is_visible():
                            return True
                    except Exception:
                        pass

            # 2. Verificação profunda via DOM JavaScript
            has_attachment = self.page.evaluate("""
                () => {
                    const inputArea = document.querySelector('rich-textarea, .input-area, .chat-input, form');
                    if (inputArea) {
                        const imgs = inputArea.querySelectorAll('img');
                        if (imgs.length > 0) return true;
                        const preview = inputArea.querySelector('.attachment-container, attachment-preview, [data-test-id*="attachment"], mat-chip');
                        if (preview) return true;
                    }
                    const anyPreview = document.querySelectorAll('attachment-preview, .attachment-container, [data-test-id="attachment-thumbnail"], .image-preview');
                    return anyPreview.length > 0;
                }
            """)
            return bool(has_attachment)
        except Exception:
            return False

    def _wait_for_attachment(self, timeout_sec: float = 6.0) -> bool:
        """Aguarda até que a miniatura da imagem anexada apareça na interface."""
        start = time.time()
        while (time.time() - start) < timeout_sec:
            if self._is_attachment_present():
                return True
            self.page.wait_for_timeout(350)
        return False

    def _upload_image(self, image_path: Path) -> None:
        """Realiza o upload da imagem colando via Clipboard (Ctrl+V) ou fallback via seletor de arquivo."""
        self.logger.info(f"📋 Preparando imagem para anexo: {image_path.name}")
        abs_path = str(image_path.resolve())

        # 1. Copia a imagem para o clipboard ANTES de focar o navegador
        copied = copy_image_to_clipboard(image_path)
        time.sleep(0.3)

        # Garante foco no navegador e no campo de prompt
        try:
            self.page.bring_to_front()
        except Exception:
            pass

        prompt_box = self.page.locator(GeminiSelectors.PROMPT_INPUT).first
        prompt_box.wait_for(state="visible", timeout=10000)
        prompt_box.click()
        self.page.wait_for_timeout(400)

        # Tentativa 1 via Clipboard do Windows (Ctrl+V)
        if copied:
            self.logger.info("📌 Colando imagem no Gemini com Ctrl+V...")
            self.page.keyboard.press("Control+v")
            if self._wait_for_attachment(timeout_sec=4.5):
                self.logger.info("✅ Miniatura do anexo confirmada no DOM via Ctrl+V.")
                return

            # Tentativa 2 com refoco do prompt (caso a primeira tenha apenas focado a janela)
            self.logger.info("Tentando refocar caixa de texto e reenviar Ctrl+V...")
            prompt_box.click()
            self.page.wait_for_timeout(600)
            self.page.keyboard.press("Control+v")
            if self._wait_for_attachment(timeout_sec=5.0):
                self.logger.info("✅ Miniatura do anexo confirmada no DOM no segundo Ctrl+V.")
                return

            self.logger.warning("⚠️ Ctrl+V executado, mas a miniatura não apareceu. Acionando fallback...")

        # 2. Tentativa via Input de Arquivo nativo (input[type='file'])
        try:
            file_inputs = self.page.locator(GeminiSelectors.FILE_INPUT)
            if file_inputs.count() > 0:
                self.logger.info("📁 Enviando arquivo via seletor de arquivo DOM...")
                file_inputs.first.set_input_files(abs_path)
                if self._wait_for_attachment(timeout_sec=7.0):
                    self.logger.info("✅ Miniatura do anexo confirmada via seletor de arquivo.")
                    return
        except Exception as e:
            self.logger.debug(f"Fallback via input de arquivo falhou: {e}")

        # 3. Tentativa via Botão de Anexo (+) -> File Chooser
        try:
            attach_btn = self.page.locator(GeminiSelectors.ATTACH_BUTTON).first
            if attach_btn.is_visible():
                self.logger.info("📎 Acionando botão de anexo (+) na interface...")
                with self.page.expect_file_chooser(timeout=5000) as fc_info:
                    attach_btn.click()
                    self.page.wait_for_timeout(300)
                    upload_item = self.page.locator(GeminiSelectors.UPLOAD_MENU_ITEM).first
                    if upload_item.is_visible():
                        upload_item.click()
                file_chooser = fc_info.value
                file_chooser.set_files(abs_path)
                if self._wait_for_attachment(timeout_sec=7.0):
                    self.logger.info("✅ Miniatura confirmada após seleção de arquivo.")
                    return
        except Exception as e:
            self.logger.debug(f"Fallback via botão de anexo falhou: {e}")

        # Checagem final
        if self._is_attachment_present():
            self.logger.info("✅ Anexo detectado com sucesso na checagem final.")
            return

        raise RuntimeError(f"Falha ao anexar a imagem '{image_path.name}' por todos os métodos.")

    def _inject_prompt_and_send(self, prompt_text: str) -> None:
        """Digita o prompt técnico especializado mantendo a imagem anexada e envia a mensagem."""
        self.logger.info("Injetando prompt especializado no editor...")
        prompt_box = self.page.locator(GeminiSelectors.PROMPT_INPUT).first
        prompt_box.click()
        self.page.wait_for_timeout(300)

        # Usa insert_text em vez de keyboard.type para que quebras de linha (\n)
        # NÃO acionem o envio prematuro da mensagem via tecla Enter
        self.page.keyboard.insert_text(prompt_text)
        self.page.wait_for_timeout(1000)

        # Envia a mensagem após o texto completo estar inserido
        send_btn = self.page.locator(GeminiSelectors.SEND_BUTTON).first
        if send_btn.is_visible() and send_btn.is_enabled():
            send_btn.click()
        else:
            self.page.wait_for_timeout(500)
            if send_btn.is_visible() and send_btn.is_enabled():
                send_btn.click()
            else:
                prompt_box.press("Enter")

        self.logger.info("Prompt enviado com sucesso. Aguardando geração da IA...")

    def _to_high_res_google_url(self, url: str) -> str:
        """Converte URLs do googleusercontent para requisitar a resolução nativa original sem compressão (=s0)."""
        if "googleusercontent.com" in url:
            import re
            if "=" in url:
                return re.sub(r'=[^/]+$', '=s0', url)
            else:
                return f"{url}=s0"
        return url

    def _extract_generated_model_image(self) -> Optional[bytes]:
        """Extrai exclusivamente a imagem gerada na RESPOSTA DO MODELO (ignorando a imagem enviada pelo usuário)."""
        try:
            if self.page.is_closed():
                return None

            # 1. Busca por locators do Playwright diretamente nos cards de resposta (atravessa Shadow DOM nativamente)
            model_cards = self.page.locator("model-response, .model-response, [data-test-id='model-response']")
            if model_cards.count() > 0:
                last_card = model_cards.last

                # 1.1 Verifica se há link direto de download no card
                dl_link = last_card.locator("a[download], a[href*='googleusercontent']").first
                try:
                    if dl_link.count() > 0 and dl_link.is_visible():
                        href = dl_link.get_attribute("href")
                        if href and href.startswith("http"):
                            high_res_href = self._to_high_res_google_url(href)
                            resp = self.context.request.get(high_res_href)
                            if resp.ok and len(resp.body()) > 40000:
                                return resp.body()
                except Exception:
                    pass

                # 1.2 Inspeciona todas as tags img dentro do card de resposta
                card_imgs = last_card.locator("img").all()
                for img_loc in reversed(card_imgs):
                    try:
                        box = img_loc.bounding_box()
                        if box and (box["width"] < 100 or box["height"] < 100):
                            continue

                        src = img_loc.get_attribute("src") or img_loc.get_attribute("currentSrc")
                        if not src:
                            continue
                        if any(bad in src.lower() for bad in ("avatar", "profile", "emoji", "icon", "gstatic", "favicon", "placeholder")):
                            continue

                        # Se for data URL
                        if src.startswith("data:image") and "," in src:
                            _, encoded = src.split(",", 1)
                            b = base64.b64decode(encoded)
                            if len(b) > 20000:
                                return b

                        # Se for blob URL
                        if src.startswith("blob:"):
                            blob_data = self.page.evaluate("""
                                async (blobUrl) => {
                                    try {
                                        const res = await fetch(blobUrl);
                                        const blob = await res.blob();
                                        return new Promise((resolve) => {
                                            const reader = new FileReader();
                                            reader.onloadend = () => resolve(reader.result);
                                            reader.readAsDataURL(blob);
                                        });
                                    } catch (e) {
                                        return null;
                                    }
                                }
                            """, src)
                            if blob_data and "," in blob_data:
                                _, encoded = blob_data.split(",", 1)
                                b = base64.b64decode(encoded)
                                if len(b) > 20000:
                                    return b

                        # Se for URL HTTP/HTTPS
                        if src.startswith("http"):
                            # Solicita a resolução original nativa do Google sem compressão (=s0)
                            high_res_src = self._to_high_res_google_url(src)
                            resp = self.context.request.get(high_res_src)
                            if resp.ok and len(resp.body()) > 20000:
                                return resp.body()
                    except Exception:
                        pass

            # 2. Fallback via JavaScript com busca recursiva no Shadow DOM
            img_info = self.page.evaluate("""
                async () => {
                    function findImagesDeep(node) {
                        let res = [];
                        if (!node) return res;
                        if (node.querySelectorAll) {
                            res.push(...Array.from(node.querySelectorAll('img')));
                        }
                        if (node.shadowRoot) {
                            res.push(...findImagesDeep(node.shadowRoot));
                        }
                        const children = node.children || [];
                        for (let i = 0; i < children.length; i++) {
                            res.push(...findImagesDeep(children[i]));
                        }
                        return res;
                    }

                    const allImgs = findImagesDeep(document.body);
                    const valid = allImgs.filter(img => {
                        const inUser = img.closest && img.closest('user-query, .user-query, rich-textarea, .attachment-container, .input-area');
                        if (inUser) return false;
                        const src = img.currentSrc || img.src || '';
                        if (!src || src.includes('avatar') || src.includes('profile') || src.includes('emoji') || src.includes('gstatic') || src.includes('placeholder')) return false;
                        const w = img.naturalWidth || img.clientWidth || 0;
                        const h = img.naturalHeight || img.clientHeight || 0;
                        return (w >= 180 && h >= 180) && (src.includes('googleusercontent.com') || src.startsWith('blob:') || src.startsWith('data:image'));
                    });

                    if (valid.length > 0) {
                        const target = valid[valid.length - 1];
                        const src = target.currentSrc || target.src || '';
                        if (src.startsWith('data:image')) {
                            return { type: 'data_url', data: src };
                        }
                        if (src.startsWith('blob:')) {
                            try {
                                const res = await fetch(src);
                                const blob = await res.blob();
                                return new Promise((resolve) => {
                                    const reader = new FileReader();
                                    reader.onloadend = () => resolve({ type: 'data_url', data: reader.result });
                                    reader.readAsDataURL(blob);
                                });
                            } catch (e) {
                                return null;
                            }
                        }
                        return { type: 'url', data: src };
                    }
                    return null;
                }
            """)

            if img_info:
                img_type = img_info.get("type")
                data = img_info.get("data")
                if img_type == "data_url" and data and "," in data:
                    _, encoded = data.split(",", 1)
                    b = base64.b64decode(encoded)
                    if len(b) > 20000:
                        return b
                elif img_type == "url" and data and data.startswith("http"):
                    high_res_url = self._to_high_res_google_url(data)
                    resp = self.context.request.get(high_res_url)
                    if resp.ok and len(resp.body()) > 20000:
                        return resp.body()

        except Exception as e:
            self.logger.debug(f"Extração da imagem do modelo falhou: {e}")

        return None

    def _wait_and_download_result(self, target_output_path: Path) -> Path:
        """Aguarda a conclusão total do processamento da IA e salva a imagem gerada."""
        start_time = time.time()
        timeout_sec = self.settings.timeout_ms / 1000.0

        self.logger.info("Aguardando IA processar e gerar a nova imagem de alta resolução...")

        temp_dl_dir = self.settings.data_dir / "temp_downloads"
        temp_dl_dir.mkdir(parents=True, exist_ok=True)
        user_dl_dir = Path.home() / "Downloads"

        initial_temp_files = set(temp_dl_dir.glob("*"))
        initial_user_dl_files = set(user_dl_dir.glob("*")) if user_dl_dir.exists() else set()

        def find_fresh_downloaded_file() -> Optional[Path]:
            """Verifica se novo arquivo de imagem ou download recente surgiu em temp_downloads ou na pasta Downloads do sistema."""
            dirs_to_check = [
                (temp_dl_dir, initial_temp_files),
                (user_dl_dir, initial_user_dl_files)
            ]
            candidates = []
            for d, initial_set in dirs_to_check:
                if not d.exists():
                    continue
                try:
                    for f in d.glob("*"):
                        if f.is_file() and f not in initial_set:
                            try:
                                mtime = f.stat().st_mtime
                                if mtime < (start_time - 3.0):
                                    continue
                                sz = f.stat().st_size
                                if sz > 20000:
                                    candidates.append(f)
                            except Exception:
                                pass
                except Exception:
                    pass
            if candidates:
                latest = max(candidates, key=lambda x: x.stat().st_mtime)
                # Aguarda estabilização de escrita se ainda estiver crescendo
                prev_size = -1
                for _ in range(10):
                    try:
                        cur_size = latest.stat().st_size
                        if cur_size == prev_size and cur_size > 50000:
                            break
                        prev_size = cur_size
                    except Exception:
                        pass
                    time.sleep(0.5)
                try:
                    from PIL import Image
                    with Image.open(latest) as im:
                        im.verify()
                    import shutil
                    shutil.copy(str(latest), str(target_output_path))
                    self.logger.info(f"✅ Arquivo de imagem recuperado com sucesso: {target_output_path.name} ({latest.name})")
                    return target_output_path
                except Exception:
                    pass
            return None

        # Listener para capturar downloads disparados a qualquer momento em segundo plano
        downloaded_items = []

        def on_download_event(download):
            self.logger.info(f"📥 Evento de download recebido do navegador: {download.suggested_filename}")
            downloaded_items.append(download)

        try:
            self.page.on("download", on_download_event)
        except Exception:
            pass

        # Espera inicial para início da geração
        time.sleep(3.0)
        last_download_attempt_time = 0.0

        try:
            while (time.time() - start_time) < timeout_sec:
                if self.page.is_closed():
                    recovered = find_fresh_downloaded_file()
                    if recovered:
                        return recovered
                    raise RuntimeError("A página do navegador foi fechada inesperadamente.")

                # 1. Verifica se algum download já foi concluído pelo listener
                if downloaded_items:
                    dl = downloaded_items[0]
                    try:
                        self.logger.info(f"Gravando arquivo de download ({dl.suggested_filename})...")
                        dl.save_as(str(target_output_path.resolve()))
                        if target_output_path.exists() and target_output_path.stat().st_size > 2000:
                            self.logger.info(f"✅ Download oficial concluído via listener ({target_output_path.stat().st_size / 1024:.1f} KB): {target_output_path.name}")
                            return target_output_path
                    except Exception as err:
                        self.logger.debug(f"save_as do listener aguardando conclusão: {err}")

                # 2. Verifica se novo arquivo surgiu na pasta de downloads temporária ou de usuário
                fresh = find_fresh_downloaded_file()
                if fresh:
                    return fresh

                # 3. Verifica se o Gemini REALMENTE ainda está gerando (sem falsos positivos)
                is_still_generating = False
                try:
                    generating = self.page.locator(
                        "button[aria-label*='Stop' i], button[aria-label*='Interromper' i], button[aria-label*='Parar' i], mat-progress-bar, [role='progressbar']"
                    )
                    for i in range(generating.count()):
                        try:
                            if generating.nth(i).is_visible():
                                is_still_generating = True
                                break
                        except Exception:
                            pass
                except Exception:
                    pass

                # 4. PRIORIDADE 1: Extração direta da imagem com URL em resolução nativa máxima (=s0)
                if not is_still_generating and (time.time() - start_time) > 8.0:
                    raw_bytes = self._extract_generated_model_image()
                    if raw_bytes:
                        target_output_path.write_bytes(raw_bytes)
                        self.logger.info(
                            f"✅ Imagem original extraída em resolução máxima ({len(raw_bytes) / 1024:.1f} KB) em: {target_output_path.name}"
                        )
                        return target_output_path

                # 5. PRIORIDADE 2: Aciona o botão oficial de Download Nativo do Gemini
                if not is_still_generating and (time.time() - start_time) > 8.0 and (time.time() - last_download_attempt_time) > 6.0:
                    last_download_attempt_time = time.time()
                    try:
                        model_cards = self.page.locator("model-response, .model-response, [data-test-id='model-response'], message-content")
                        if model_cards.count() > 0:
                            last_card = model_cards.last

                            # Passa o mouse sobre a imagem do card para revelar os botões flutuantes de ação
                            card_img = last_card.locator("img").last
                            if card_img.is_visible():
                                try:
                                    card_img.hover(timeout=1500)
                                    self.page.wait_for_timeout(400)
                                except Exception:
                                    pass

                            download_btn = self.page.locator(GeminiSelectors.DOWNLOAD_BUTTON).last

                            if download_btn.count() > 0:
                                self.logger.info("Acionando botão oficial de Download [data-test-id='image-download-button']...")
                                try:
                                    with self.page.expect_download(timeout=40000) as dl_info:
                                        download_btn.click(force=True)
                                    dl = dl_info.value
                                    self.logger.info(f"📥 Concluindo gravação de: {dl.suggested_filename}")
                                    dl.save_as(str(target_output_path.resolve()))
                                    if target_output_path.exists() and target_output_path.stat().st_size > 2000:
                                        self.logger.info(f"✅ Imagem original baixada em alta resolução: {target_output_path.name}")
                                        return target_output_path
                                except Exception as click_err:
                                    self.logger.debug(f"expect_download com clique inicial: {click_err}")

                                # Se o clique inicial não retornou diretamente, checa o listener ou arquivo recente
                                if downloaded_items:
                                    try:
                                        dl = downloaded_items[0]
                                        dl.save_as(str(target_output_path.resolve()))
                                        if target_output_path.exists() and target_output_path.stat().st_size > 2000:
                                            self.logger.info(f"✅ Imagem salva a partir do evento de download: {target_output_path.name}")
                                            return target_output_path
                                    except Exception:
                                        pass

                                fresh_after_click = find_fresh_downloaded_file()
                                if fresh_after_click:
                                    return fresh_after_click

                    except Exception as e:
                        self.logger.debug(f"Tentativa de download nativo gerou aviso suave: {e}")

                try:
                    if not self.page.is_closed():
                        self.page.wait_for_timeout(1500)
                    else:
                        time.sleep(1.5)
                except Exception:
                    time.sleep(1.5)

            raise PlaywrightTimeoutError(
                f"Tempo limite excedido ({timeout_sec:.0f}s) aguardando a imagem gerada pelo Gemini."
            )
        finally:
            try:
                self.page.remove_listener("download", on_download_event)
            except Exception:
                pass

    def process_single_image(
        self,
        image_path: Path,
        profile: ProductProfile,
        orientation: str = "auto",
        card_style: Optional[str] = None,
        force: bool = False
    ) -> Path:
        target_output_path = profile.get_target_output_path(image_path, self.settings.data_dir)
        rel_display = str(profile.get_relative_input_path(image_path, self.settings.data_dir))

        # Idempotência: Ignora se já existir e não for forçado
        if not force and target_output_path.exists() and target_output_path.stat().st_size > 0:
            self.logger.info(f"[IDEMPOTÊNCIA] Arquivo já processado anteriormente: {rel_display}")
            return target_output_path

        self.logger.info(f"=== Iniciando Upscaling para '{rel_display}' | Perfil: {profile.display_name} ===")

        last_error = None
        for attempt in range(1, 3):
            try:
                # 1. Prepara novo chat
                self.ensure_chat_ready()

                # 2. Faz upload da imagem colando via Ctrl+V ou fallback
                self._upload_image(image_path)

                # 3. Gera o prompt técnico adaptado (respeitando dimensões verticais ou horizontais)
                prompt_text = profile.get_prompt_for_image(
                    image_path=image_path,
                    orientation=orientation,
                    card_style=card_style,
                    logger=self.logger
                )

                # 4. Digita o prompt técnico e dispara o envio
                self._inject_prompt_and_send(prompt_text)

                # 5. Aguarda e baixa o resultado gerado
                saved_path = self._wait_and_download_result(target_output_path)

                # 6. Calibração física exata de medidas em mm e 300 DPI mantendo os elementos
                if profile.product_type == ProductType.CARD_BACK:
                    from src.card_back import CardBleedEngine
                    eff_mm = profile.get_effective_dimensions_mm(orientation=orientation, image_path=image_path)
                    bleed_mm = (eff_mm[0] - 63.5) / 2.0 if eff_mm[0] > 63.5 else 5.0
                    CardBleedEngine.apply_bleed(
                        image_input=saved_path,
                        card_dimensions_mm=(63.5, 88.9),
                        bleed_mm=bleed_mm,
                        dpi=profile.target_dpi,
                        output_path=saved_path,
                        generate_proof=True,
                    )
                    proof_p = saved_path.with_name(f"{saved_path.stem}_proof.png")
                    self.logger.info(
                        f"🎴 [Verso/Fundo] Sangria industrial de +{bleed_mm:.1f}mm aplicada com sucesso! "
                        f"Arquivo final: {saved_path.name} ({eff_mm[0]:.1f}x{eff_mm[1]:.1f}mm @ {profile.target_dpi} DPI) "
                        f"| Prova técnica com guia de corte: {proof_p.name}"
                    )
                elif self.settings.exact_dimensions:
                    from src.utils import adjust_image_to_target_dimensions
                    eff_mm = profile.get_effective_dimensions_mm(orientation=orientation, image_path=image_path)
                    target_px = profile.get_target_pixel_size(orientation=orientation, image_path=image_path)
                    adjust_image_to_target_dimensions(
                        image_path=saved_path,
                        target_dimensions_mm=eff_mm,
                        target_dpi=profile.target_dpi,
                        fit_mode=self.settings.fit_mode,
                        output_path=saved_path
                    )
                    self.logger.info(
                        f"🎯 Calibração dimensional aplicada ({self.settings.fit_mode.upper()}): "
                        f"{target_px[0]}x{target_px[1]}px ({eff_mm[0]}x{eff_mm[1]}mm @ {profile.target_dpi} DPI)"
                    )

                # 7. Delay configurado entre arquivos para respeito de taxa
                time.sleep(self.settings.delay_between_files_sec)

                return saved_path
            except Exception as e:
                last_error = e
                if attempt < 2 and not self.page.is_closed():
                    self.logger.warning(
                        f"⚠️ [Tentativa {attempt}/2] Falha transitória em '{rel_display}': {e}. "
                        "Reiniciando contexto para segunda tentativa..."
                    )
                    time.sleep(3.0)
                else:
                    raise last_error


