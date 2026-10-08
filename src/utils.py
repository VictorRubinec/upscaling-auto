import functools
import logging
import struct
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Optional, Tuple, Type
import requests


def setup_logger(log_file: Path, name: str = "GeminiUpscaler") -> logging.Logger:
    """Configura um logger com saída simultânea para console e arquivo com formatação padronizada."""
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Evita duplicação de handlers caso seja chamado mais de uma vez
    if logger.hasHandlers():
        logger.handlers.clear()

    formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    # Handler para o Console (sys.stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Handler para Arquivo
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def retry(
    max_attempts: int = 3,
    delay_sec: float = 3.0,
    backoff: float = 1.5,
    exceptions: Tuple[Type[BaseException], ...] = (Exception,)
) -> Callable:
    """Decorator de retentativa resiliente para operações com o navegador e rede."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            current_delay = delay_sec
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    logger = logging.getLogger("GeminiUpscaler")
                    if attempt < max_attempts:
                        logger.warning(
                            f"[Tentativa {attempt}/{max_attempts}] Falha em '{func.__name__}': {str(e)}. "
                            f"Aguardando {current_delay:.1f}s antes de retentar..."
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"[Tentativa {attempt}/{max_attempts}] Todas as tentativas falharam para '{func.__name__}': {str(e)}"
                        )
            if last_exception:
                raise last_exception
        return wrapper
    return decorator


def is_cdp_available(cdp_url: str = "http://127.0.0.1:9222") -> bool:
    """Verifica se há um navegador rodando com porta de depuração remota (CDP) ativa."""
    try:
        res = requests.get(f"{cdp_url}/json/version", timeout=1.5)
        return res.status_code == 200
    except Exception:
        return False


def copy_image_to_clipboard(image_path: Path) -> bool:
    """Copia a imagem para a área de transferência do Windows para colar via Ctrl+V no Gemini."""
    abs_path = str(image_path.resolve()).replace("'", "''")
    # Tentativa 1: Injeta como Bitmap e como Arquivo (DataObject)
    ps_script = (
        "Add-Type -AssemblyName System.Windows.Forms; "
        "Add-Type -AssemblyName System.Drawing; "
        f"$filePath = '{abs_path}'; "
        "$dataObj = New-Object System.Windows.Forms.DataObject; "
        "try { "
        "  $img = [System.Drawing.Image]::FromFile($filePath); "
        "  $dataObj.SetImage($img); "
        "  $img.Dispose(); "
        "} catch {} "
        "$fileCol = New-Object System.Collections.Specialized.StringCollection; "
        "$fileCol.Add($filePath); "
        "$dataObj.SetFileDropList($fileCol); "
        "[System.Windows.Forms.Clipboard]::SetDataObject($dataObj, $true);"
    )
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=8
        )
        if res.returncode == 0:
            return True
    except Exception:
        pass

    # Fallback via Set-Clipboard nativo do PowerShell
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", f"Set-Clipboard -LiteralPath '{abs_path}'"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return True
    except Exception:
        return False


def get_image_size(file_path: Path) -> Optional[Tuple[int, int]]:
    """Lê as dimensões (largura, altura) em pixels de imagens PNG, JPEG, WEBP ou BMP em Python puro."""
    try:
        with open(file_path, "rb") as f:
            data = f.read(256)
            if len(data) < 24:
                return None

            # PNG
            if data.startswith(b"\x89PNG\r\n\x1a\n"):
                w, h = struct.unpack(">II", data[16:24])
                return w, h

            # BMP
            if data[:2] == b"BM":
                w, h = struct.unpack("<II", data[18:26])
                return w, h

            # WEBP
            if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
                subtype = data[12:16]
                if subtype == b"VP8 ":
                    w, h = struct.unpack("<HH", data[26:30])
                    return w & 0x3FFF, h & 0x3FFF
                elif subtype == b"VP8L":
                    b1, b2, b3, b4 = data[21:25]
                    w = 1 + (((b2 & 0x3F) << 8) | b1)
                    h = 1 + (((b4 & 0x0F) << 10) | (b3 << 2) | ((b2 & 0xC0) >> 6))
                    return w, h
                elif subtype == b"VP8X":
                    w = 1 + struct.unpack("<I", data[24:27] + b"\x00")[0]
                    h = 1 + struct.unpack("<I", data[27:30] + b"\x00")[0]
                    return w, h

            # JPEG
            if data.startswith(b"\xff\xd8"):
                f.seek(2)
                while True:
                    marker_bytes = f.read(2)
                    if len(marker_bytes) < 2:
                        break
                    while marker_bytes[0] != 0xFF:
                        marker_bytes = marker_bytes[1:] + f.read(1)
                        if len(marker_bytes) < 2:
                            break
                    if len(marker_bytes) < 2:
                        break
                    marker = marker_bytes[1]
                    if marker in (0xD9, 0xDA):  # EOI, SOS
                        break
                    if 0xD0 <= marker <= 0xD7 or marker == 0x01:  # RST, TEM
                        continue
                    length_bytes = f.read(2)
                    if len(length_bytes) < 2:
                        break
                    length = struct.unpack(">H", length_bytes)[0]
                    if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                        sof_data = f.read(5)
                        precision, h, w = struct.unpack(">BHH", sof_data)
                        return w, h
                    f.seek(length - 2, 1)
    except Exception:
        pass
    return None


def mm_to_pixels(mm: float, dpi: int = 300) -> int:
    """Converte milímetros para pixels na resolução gráfica informada."""
    return round((mm * dpi) / 25.4)


def get_dominant_border_color(img) -> Tuple[int, int, int]:
    """Calcula a cor média/predominante das bordas de uma imagem para preenchimento harmônico."""
    rgb_img = img.convert("RGB")
    w, h = rgb_img.size
    border_pixels = []
    step_x = max(1, w // 40)
    step_y = max(1, h // 40)
    for x in range(0, w, step_x):
        border_pixels.append(rgb_img.getpixel((x, 0)))
        border_pixels.append(rgb_img.getpixel((x, h - 1)))
    for y in range(0, h, step_y):
        border_pixels.append(rgb_img.getpixel((0, y)))
        border_pixels.append(rgb_img.getpixel((w - 1, y)))

    if not border_pixels:
        return (255, 255, 255)

    r = sum(p[0] for p in border_pixels) // len(border_pixels)
    g = sum(p[1] for p in border_pixels) // len(border_pixels)
    b = sum(p[2] for p in border_pixels) // len(border_pixels)
    return (r, g, b)


def adjust_image_to_target_dimensions(
    image_path: Path,
    target_dimensions_mm: Tuple[float, float],
    target_dpi: int = 300,
    fit_mode: str = "pad",
    output_path: Optional[Path] = None
) -> Path:
    """
    Ajusta a imagem para as medidas físicas exatas em milímetros a 300 DPI,
    mantendo os elementos visuais preservados de acordo com o fit_mode escolhido:
    - 'pad': Preserva 100% da arte sem corte ou distorção, preenchendo as bordas com a cor das margens.
    - 'blur_pad': Preserva 100% da arte no centro e preenche as margens com o fundo suavemente desfocado.
    - 'crop': Preenchimento total (Aspect Fill) centralizado, cortando apenas excedentes nas bordas.
    - 'stretch': Estiramento direto para as dimensões exatas.
    - 'none': Mantém o tamanho original apenas injetando metadados de 300 DPI.
    """
    from PIL import Image, ImageFilter

    target_path = output_path or image_path
    target_w_px = mm_to_pixels(target_dimensions_mm[0], target_dpi)
    target_h_px = mm_to_pixels(target_dimensions_mm[1], target_dpi)

    with Image.open(image_path) as img:
        img_rgb = img.convert("RGB")
        cur_w, cur_h = img_rgb.size

        if fit_mode == "none":
            final_img = img_rgb
        elif fit_mode == "stretch":
            final_img = img_rgb.resize((target_w_px, target_h_px), Image.Resampling.LANCZOS)
        elif fit_mode == "crop":
            # Redimensiona para cobrir todo o canvas (scale = max)
            scale = max(target_w_px / cur_w, target_h_px / cur_h)
            scaled_w = round(cur_w * scale)
            scaled_h = round(cur_h * scale)
            scaled_img = img_rgb.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)
            # Corta centralizado
            left = (scaled_w - target_w_px) // 2
            top = (scaled_h - target_h_px) // 2
            final_img = scaled_img.crop((left, top, left + target_w_px, top + target_h_px))
        elif fit_mode == "blur_pad":
            scale = min(target_w_px / cur_w, target_h_px / cur_h)
            scaled_w = round(cur_w * scale)
            scaled_h = round(cur_h * scale)
            scaled_img = img_rgb.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)

            bg_scale = max(target_w_px / cur_w, target_h_px / cur_h)
            bg_w = round(cur_w * bg_scale)
            bg_h = round(cur_h * bg_scale)
            bg_img = img_rgb.resize((bg_w, bg_h), Image.Resampling.BILINEAR)
            bg_left = (bg_w - target_w_px) // 2
            bg_top = (bg_h - target_h_px) // 2
            bg_cropped = bg_img.crop((bg_left, bg_top, bg_left + target_w_px, bg_top + target_h_px))
            blurred_bg = bg_cropped.filter(ImageFilter.GaussianBlur(radius=35))

            paste_x = (target_w_px - scaled_w) // 2
            paste_y = (target_h_px - scaled_h) // 2
            blurred_bg.paste(scaled_img, (paste_x, paste_y))
            final_img = blurred_bg
        else:  # 'pad' (padrão)
            scale = min(target_w_px / cur_w, target_h_px / cur_h)
            scaled_w = round(cur_w * scale)
            scaled_h = round(cur_h * scale)
            scaled_img = img_rgb.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)

            border_color = get_dominant_border_color(img_rgb)
            canvas = Image.new("RGB", (target_w_px, target_h_px), color=border_color)
            paste_x = (target_w_px - scaled_w) // 2
            paste_y = (target_h_px - scaled_h) // 2
            canvas.paste(scaled_img, (paste_x, paste_y))
            final_img = canvas

        final_img.save(target_path, "PNG", dpi=(target_dpi, target_dpi))

    return target_path



