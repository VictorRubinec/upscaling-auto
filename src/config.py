import os
from enum import Enum
from pathlib import Path
from typing import Dict, Optional, Tuple
from pydantic import BaseModel, Field


class ProductType(str, Enum):
    """Tipos de produtos físicos suportados pela Studio Kustom."""
    POSTER_A4 = "POSTER_A4"
    POSTER_A3 = "POSTER_A3"
    TRADING_CARD = "TRADING_CARD"
    POLAROID = "POLAROID"
    MUG = "MUG"


class ProductProfile(BaseModel):
    """Perfil de configuração técnica e prompt de upscaling por tipo de produto."""
    product_type: ProductType
    display_name: str
    target_dimensions_mm: Tuple[float, float]
    target_dpi: int = 300
    aspect_ratio: str
    system_prompt: str
    output_suffix: str = "_upscaled_300dpi"
    input_subpath: str
    output_subpath: str

    def get_input_dir(self, base_data_dir: Path) -> Path:
        """Retorna e garante a existência do diretório de entrada para o produto."""
        path = base_data_dir / "input" / self.input_subpath
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_output_dir(self, base_data_dir: Path) -> Path:
        """Retorna e garante a existência do diretório de saída para o produto."""
        path = base_data_dir / "output" / self.output_subpath
        path.mkdir(parents=True, exist_ok=True)
        return path


# Catálogo com especificações técnicas e prompts de IA especializados
PRODUCT_REGISTRY: Dict[ProductType, ProductProfile] = {
    ProductType.POSTER_A4: ProductProfile(
        product_type=ProductType.POSTER_A4,
        display_name="Pôster Formato A4",
        target_dimensions_mm=(210.0, 297.0),
        target_dpi=300,
        aspect_ratio="1:1.414 (A4)",
        system_prompt=(
            "Upscale and enhance this image for ultra-high-definition physical print on an A4 poster (210x297mm at 300 DPI). "
            "Preserve original artistic style, composition, and colors faithfully. "
            "Remove JPEG compression artifacts, pixelation, and visual noise while sharpening edges, lines, and textures. "
            "Ensure gradients are smooth without color banding. Output the highest resolution possible."
        ),
        input_subpath="poster_a4",
        output_subpath="poster_a4",
    ),
    ProductType.POSTER_A3: ProductProfile(
        product_type=ProductType.POSTER_A3,
        display_name="Pôster Formato A3 (Grande Formato)",
        target_dimensions_mm=(297.0, 420.0),
        target_dpi=300,
        aspect_ratio="1:1.414 (A3)",
        system_prompt=(
            "Perform extreme super-resolution enhancement on this image for large-format physical poster printing (A3 format, 297x420mm at 300 DPI). "
            "Reconstruct micro-details, ultra-fine textures, and sharp contours without creating unnatural AI hallucinations. "
            "Eliminate all compression artifacts, enhance contrast subtly, and maintain strict chromatic consistency. "
            "Deliver the absolute maximum native resolution output."
        ),
        input_subpath="poster_a3",
        output_subpath="poster_a3",
    ),
    ProductType.TRADING_CARD: ProductProfile(
        product_type=ProductType.TRADING_CARD,
        display_name="Trading Card Colecionável",
        target_dimensions_mm=(63.5, 88.9),
        target_dpi=300,
        aspect_ratio="2.5:3.5 (Standard Card)",
        system_prompt=(
            "Upscale and restore this trading card artwork for high-density micro-printing (63.5x88.9mm at 300+ DPI). "
            "Prioritize extreme typographic clarity and crispness: ensure all small text, stats, borders, card frames, and symbols are sharp and perfectly legible. "
            "Preserve vector-like line art sharpness, vivid color saturation, and dark contrast without blurring edges. Generate at maximum fidelity."
        ),
        input_subpath="trading_card",
        output_subpath="trading_card",
    ),
    ProductType.POLAROID: ProductProfile(
        product_type=ProductType.POLAROID,
        display_name="Foto Estilo Polaroid",
        target_dimensions_mm=(88.0, 107.0),
        target_dpi=300,
        aspect_ratio="1:1.216 (Polaroid)",
        system_prompt=(
            "Enhance and upscale this photograph for high-quality instant photo print (88x107mm at 300 DPI). "
            "Preserve natural skin tones, hair textures, facial details, and organic film aesthetic. "
            "Remove digital sensor noise and harsh compression artifacts while maintaining genuine photographic softness and depth of field. "
            "Do not over-smooth faces. Output in maximum high definition."
        ),
        input_subpath="polaroid",
        output_subpath="polaroid",
    ),
    ProductType.MUG: ProductProfile(
        product_type=ProductType.MUG,
        display_name="Caneca Cerâmica (Panorâmica)",
        target_dimensions_mm=(200.0, 95.0),
        target_dpi=300,
        aspect_ratio="~2.1:1 (Panoramic Wrap)",
        system_prompt=(
            "Upscale and enhance this panoramic wrap artwork for ceramic mug sublimation printing (200x95mm at 300 DPI). "
            "Preserve the exact aspect ratio without any anamorphic stretching or edge warping. "
            "Boost color vibrancy and contrast appropriately for heat sublimation, sharpen logos and illustrations, and remove pixelation cleanly. "
            "Generate in maximum native resolution."
        ),
        input_subpath="mug",
        output_subpath="mug",
    ),
}


def find_brave_executable() -> Optional[Path]:
    """Tenta localizar o executável do navegador Brave instalado no sistema."""
    potential_paths = [
        Path("C:/Program Files/BraveSoftware/Brave-Browser/Application/brave.exe"),
        Path("C:/Program Files (x86)/BraveSoftware/Brave-Browser/Application/brave.exe"),
        Path(os.environ.get("LOCALAPPDATA", "")) / "BraveSoftware/Brave-Browser/Application/brave.exe",
    ]
    for p in potential_paths:
        if p.exists():
            return p
    return None


class AppSettings(BaseModel):
    """Configurações globais da aplicação e runtime do Playwright."""
    base_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent)
    gemini_url: str = "https://gemini.google.com/app"
    headless: bool = False
    timeout_ms: int = 180000  # 3 minutos por imagem
    max_retries: int = 3
    delay_between_files_sec: float = 4.0
    supported_extensions: Tuple[str, ...] = (".png", ".jpg", ".jpeg", ".webp")
    cdp_port: int = 9222

    @property
    def data_dir(self) -> Path:
        """Diretório raiz de dados."""
        path = self.base_dir / "data"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def user_data_dir(self) -> Path:
        """Diretório do perfil persistente padrão."""
        path = self.data_dir / "browser_profile"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def brave_user_data_dir(self) -> Path:
        """Diretório de dados de perfil do Brave Browser nativo."""
        return Path(os.environ.get("LOCALAPPDATA", "")) / "BraveSoftware/Brave-Browser/User Data"

    @property
    def logs_dir(self) -> Path:
        """Diretório de logs de execução."""
        path = self.data_dir / "logs"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def cdp_url(self) -> str:
        """URL para conexão via Chrome DevTools Protocol."""
        return f"http://127.0.0.1:{self.cdp_port}"
