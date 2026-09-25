import functools
import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Tuple, Type
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
    ps_script = (
        "Add-Type -AssemblyName System.Windows.Forms; "
        "Add-Type -AssemblyName System.Drawing; "
        f"$img = [System.Drawing.Image]::FromFile('{abs_path}'); "
        "[System.Windows.Forms.Clipboard]::SetImage($img); "
        "$img.Dispose();"
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

    # Fallback via Set-Clipboard nativo
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
