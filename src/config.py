import os
from enum import Enum
from pathlib import Path
from typing import Dict, Optional, Tuple
from pydantic import BaseModel, Field


class ProductType(str, Enum):
    """Tipos de produtos físicos suportados pela Studio Kustom."""
    POSTER_A4 = "POSTER_A4"
    POSTER_A4_HORIZONTAL = "POSTER_A4_HORIZONTAL"
    POSTER_A3 = "POSTER_A3"
    POSTER_A3_HORIZONTAL = "POSTER_A3_HORIZONTAL"
    TRADING_CARD = "TRADING_CARD"
    POKEMON_CARD = "POKEMON_CARD"
    ONEPIECE_CARD = "ONEPIECE_CARD"
    CARD_BACK = "CARD_BACK"
    POLAROID = "POLAROID"
    MUG = "MUG"


class ProductProfile(BaseModel):
    """Perfil de configuração técnica e prompt de upscaling por tipo de produto."""
    product_type: ProductType
    display_name: str
    target_dimensions_mm: Tuple[float, float]
    target_dpi: int = 300
    aspect_ratio: str
    default_orientation: str = "vertical"
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

    def get_relative_input_path(self, image_path: Path, base_data_dir: Path) -> Path:
        """Retorna o caminho relativo da imagem em relação ao diretório raiz de entrada do produto."""
        input_root = self.get_input_dir(base_data_dir)
        try:
            return image_path.resolve().relative_to(input_root.resolve())
        except ValueError:
            return Path(image_path.name)

    def get_target_output_path(self, image_path: Path, base_data_dir: Path) -> Path:
        """
        Retorna o caminho completo de saída correspondente a uma imagem de entrada,
        preservando qualquer estrutura de subpastas relativas (ex: por pedido, cliente ou lote)
        existente dentro de data/input/<produto>/. Cria a subpasta de destino se não existir.
        """
        input_root = self.get_input_dir(base_data_dir)
        output_root = self.get_output_dir(base_data_dir)
        try:
            rel_path = image_path.resolve().relative_to(input_root.resolve())
            target_dir = output_root / rel_path.parent
        except ValueError:
            # Caso venha de outra subpasta sob data/input/ (ex: data/input/trading_card/145/back.jpg)
            data_input = (base_data_dir / "input").resolve()
            data_output = (base_data_dir / "output").resolve()
            try:
                rel_to_input = image_path.resolve().relative_to(data_input)
                target_dir = data_output / rel_to_input.parent
            except ValueError:
                target_dir = output_root

        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir / f"{image_path.stem}{self.output_suffix}.png"

    def get_effective_dimensions_mm(self, orientation: str = "auto", image_path: Optional[Path] = None) -> Tuple[float, float]:
        """Retorna as medidas em mm respeitando a orientação horizontal/vertical."""
        from src.utils import get_image_size
        dim_w, dim_h = self.target_dimensions_mm

        is_poster = "POSTER" in self.product_type.value
        if not is_poster:
            return (dim_w, dim_h)

        is_horizontal = "HORIZONTAL" in self.product_type.value
        if orientation == "horizontal":
            is_horizontal = True
        elif orientation == "vertical":
            is_horizontal = False
        elif orientation == "auto" and image_path and image_path.exists():
            dims = get_image_size(image_path)
            if dims and dims[0] > dims[1]:
                is_horizontal = True

        long_side = max(dim_w, dim_h)
        short_side = min(dim_w, dim_h)
        return (long_side, short_side) if is_horizontal else (short_side, long_side)

    def get_target_pixel_size(self, orientation: str = "auto", image_path: Optional[Path] = None) -> Tuple[int, int]:
        """Retorna a largura e altura exatas em pixels a 300 DPI."""
        from src.utils import mm_to_pixels
        eff_w, eff_h = self.get_effective_dimensions_mm(orientation=orientation, image_path=image_path)
        return (mm_to_pixels(eff_w, self.target_dpi), mm_to_pixels(eff_h, self.target_dpi))


    def get_prompt_for_image(
        self,
        image_path: Optional[Path] = None,
        orientation: str = "auto",
        card_style: Optional[str] = None,
        logger = None
    ) -> str:
        """
        Retorna o prompt otimizado para o arquivo de imagem, aplicando detecção
        automática ou forçada de orientação (vertical x horizontal) e ajustando
        as medidas físicas em milímetros.
        """
        if self.product_type == ProductType.POKEMON_CARD:
            if image_path and image_path.exists():
                from src.pokemon import PokemonCardManager, PokemonCardPromptBuilder, CardStyle
                card = PokemonCardManager.load_card_for_image(image_path)
                if card_style:
                    for s in CardStyle:
                        if s.value.lower() == card_style.lower():
                            card.style = s
                            break
                if logger:
                    logger.info(
                        f"🃏 [Pokémon TCG] Carregada ficha da carta: '{card.name}' "
                        f"(HP: {card.hp}, Tipo: {card.energy_type.value}, Estilo: {card.style.value.upper()})"
                    )
                return PokemonCardPromptBuilder.build_prompt(card)
            return self.system_prompt

        if self.product_type == ProductType.ONEPIECE_CARD:
            if image_path and image_path.exists():
                from src.tcg.onepiece import OnePieceCardManager, OnePiecePromptBuilder, OpCardStyle
                card = OnePieceCardManager.load_card_for_image(image_path)
                if card_style:
                    for s in OpCardStyle:
                        if s.value.lower() == card_style.lower():
                            card.style = s
                            break
                if logger:
                    logger.info(
                        f"🏴‍☠️ [One Piece TCG] Carregada ficha da carta: '{card.name}' "
                        f"(Custo: {card.cost}, Cor: {card.color.value}, Estilo: {card.style.value.upper()})"
                    )
                return OnePiecePromptBuilder.build_prompt(card)
            return self.system_prompt

        if self.product_type == ProductType.CARD_BACK:
            from src.card_back import CardBackPromptBuilder
            eff_mm = self.get_effective_dimensions_mm(orientation=orientation, image_path=image_path)
            bleed_mm = (eff_mm[0] - 63.5) / 2.0 if eff_mm[0] > 63.5 else 5.0
            if logger:
                logger.info(
                    f"🎴 [Verso/Fundo] Aplicando prompt de sangria (+{bleed_mm:.1f}mm cada lado, {eff_mm[0]:.1f}x{eff_mm[1]:.1f}mm @ {self.target_dpi} DPI)"
                )
            return CardBackPromptBuilder.build_prompt(
                image_path=image_path,
                bleed_mm=bleed_mm,
                target_dimensions_mm=eff_mm
            )

        is_poster = self.product_type in (
            ProductType.POSTER_A4,
            ProductType.POSTER_A4_HORIZONTAL,
            ProductType.POSTER_A3,
            ProductType.POSTER_A3_HORIZONTAL,
        )

        if not is_poster:
            return self.system_prompt

        detected_orientation = None
        dims = None
        if image_path and image_path.exists():
            from src.utils import get_image_size
            dims = get_image_size(image_path)
            if dims:
                w, h = dims
                if w > h:
                    detected_orientation = "horizontal"
                elif h > w:
                    detected_orientation = "vertical"

        # Define orientação final
        if orientation in ("vertical", "horizontal"):
            final_orientation = orientation
        elif orientation == "auto" and detected_orientation:
            final_orientation = detected_orientation
        elif "HORIZONTAL" in self.product_type.value:
            final_orientation = "horizontal"
        else:
            final_orientation = self.default_orientation

        if logger and image_path and dims and detected_orientation:
            logger.info(
                f"📐 Imagem '{image_path.name}' analisada: {dims[0]}x{dims[1]}px "
                f"| Orientação aplicada: {final_orientation.upper()}"
            )

        is_a3 = "A3" in self.product_type.value

        if final_orientation == "horizontal":
            if is_a3:
                return (
                    "Perform extreme super-resolution enhancement on this image for large-format physical poster printing "
                    "(A3 horizontal/landscape format, 420x297mm at 300 DPI). "
                    "Reconstruct micro-details, ultra-fine textures, and sharp contours without creating unnatural AI hallucinations. "
                    "Eliminate all compression artifacts, enhance contrast subtly, and maintain strict chromatic consistency. "
                    "Maintain strict landscape/horizontal orientation without rotating or cropping to portrait. "
                    "Deliver the absolute maximum native resolution output."
                )
            else:
                return (
                    "Upscale and enhance this image for ultra-high-definition physical print on a horizontal (landscape) A4 poster "
                    "(297x210mm at 300 DPI). "
                    "Preserve original artistic style, composition, and colors faithfully. "
                    "Remove JPEG compression artifacts, pixelation, and visual noise while sharpening edges, lines, and textures. "
                    "Ensure gradients are smooth without color banding. "
                    "Maintain strict landscape/horizontal orientation without rotating or cropping to portrait. "
                    "Output the highest resolution possible."
                )
        else:
            if is_a3:
                return (
                    "Perform extreme super-resolution enhancement on this image for large-format physical poster printing "
                    "(A3 vertical/portrait format, 297x420mm at 300 DPI). "
                    "Reconstruct micro-details, ultra-fine textures, and sharp contours without creating unnatural AI hallucinations. "
                    "Eliminate all compression artifacts, enhance contrast subtly, and maintain strict chromatic consistency. "
                    "Maintain strict portrait/vertical orientation without rotating or cropping to landscape. "
                    "Deliver the absolute maximum native resolution output."
                )
            else:
                return (
                    "Upscale and enhance this image for ultra-high-definition physical print on a vertical (portrait) A4 poster "
                    "(210x297mm at 300 DPI). "
                    "Preserve original artistic style, composition, and colors faithfully. "
                    "Remove JPEG compression artifacts, pixelation, and visual noise while sharpening edges, lines, and textures. "
                    "Ensure gradients are smooth without color banding. "
                    "Maintain strict portrait/vertical orientation without rotating or cropping to landscape. "
                    "Output the highest resolution possible."
                )


# Catálogo com especificações técnicas e prompts de IA especializados
PRODUCT_REGISTRY: Dict[ProductType, ProductProfile] = {
    ProductType.POSTER_A4: ProductProfile(
        product_type=ProductType.POSTER_A4,
        display_name="Pôster Formato A4 (Vertical / Padrão)",
        target_dimensions_mm=(210.0, 297.0),
        target_dpi=300,
        aspect_ratio="1:1.414 (A4 Retrato)",
        default_orientation="vertical",
        system_prompt=(
            "Upscale and enhance this image for ultra-high-definition physical print on a vertical (portrait) A4 poster (210x297mm at 300 DPI). "
            "Preserve original artistic style, composition, and colors faithfully. "
            "Remove JPEG compression artifacts, pixelation, and visual noise while sharpening edges, lines, and textures. "
            "Ensure gradients are smooth without color banding. "
            "Maintain strict portrait/vertical orientation without rotating or cropping to landscape. Output the highest resolution possible."
        ),
        input_subpath="poster_a4",
        output_subpath="poster_a4",
    ),
    ProductType.POSTER_A4_HORIZONTAL: ProductProfile(
        product_type=ProductType.POSTER_A4_HORIZONTAL,
        display_name="Pôster Formato A4 (Horizontal / Paisagem)",
        target_dimensions_mm=(297.0, 210.0),
        target_dpi=300,
        aspect_ratio="1.414:1 (A4 Paisagem)",
        default_orientation="horizontal",
        system_prompt=(
            "Upscale and enhance this image for ultra-high-definition physical print on a horizontal (landscape) A4 poster (297x210mm at 300 DPI). "
            "Preserve original artistic style, composition, and colors faithfully. "
            "Remove JPEG compression artifacts, pixelation, and visual noise while sharpening edges, lines, and textures. "
            "Ensure gradients are smooth without color banding. "
            "Maintain strict landscape/horizontal orientation without rotating or cropping to portrait. Output the highest resolution possible."
        ),
        input_subpath="poster_a4_horizontal",
        output_subpath="poster_a4_horizontal",
    ),
    ProductType.POSTER_A3: ProductProfile(
        product_type=ProductType.POSTER_A3,
        display_name="Pôster Formato A3 (Vertical / Grande Formato)",
        target_dimensions_mm=(297.0, 420.0),
        target_dpi=300,
        aspect_ratio="1:1.414 (A3 Retrato)",
        default_orientation="vertical",
        system_prompt=(
            "Perform extreme super-resolution enhancement on this image for large-format physical poster printing (A3 vertical/portrait format, 297x420mm at 300 DPI). "
            "Reconstruct micro-details, ultra-fine textures, and sharp contours without creating unnatural AI hallucinations. "
            "Eliminate all compression artifacts, enhance contrast subtly, and maintain strict chromatic consistency. "
            "Maintain strict portrait/vertical orientation without rotating or cropping to landscape. Deliver the absolute maximum native resolution output."
        ),
        input_subpath="poster_a3",
        output_subpath="poster_a3",
    ),
    ProductType.POSTER_A3_HORIZONTAL: ProductProfile(
        product_type=ProductType.POSTER_A3_HORIZONTAL,
        display_name="Pôster Formato A3 (Horizontal / Paisagem)",
        target_dimensions_mm=(420.0, 297.0),
        target_dpi=300,
        aspect_ratio="1.414:1 (A3 Paisagem)",
        default_orientation="horizontal",
        system_prompt=(
            "Perform extreme super-resolution enhancement on this image for large-format physical poster printing (A3 horizontal/landscape format, 420x297mm at 300 DPI). "
            "Reconstruct micro-details, ultra-fine textures, and sharp contours without creating unnatural AI hallucinations. "
            "Eliminate all compression artifacts, enhance contrast subtly, and maintain strict chromatic consistency. "
            "Maintain strict landscape/horizontal orientation without rotating or cropping to portrait. Deliver the absolute maximum native resolution output."
        ),
        input_subpath="poster_a3_horizontal",
        output_subpath="poster_a3_horizontal",
    ),
    ProductType.TRADING_CARD: ProductProfile(
        product_type=ProductType.TRADING_CARD,
        display_name="Trading Card Colecionável",
        target_dimensions_mm=(63.5, 88.9),
        target_dpi=300,
        aspect_ratio="2.5:3.5 (Standard Card)",
        default_orientation="vertical",
        system_prompt=(
            "Upscale and restore this trading card artwork for high-density micro-printing (63.5x88.9mm at 300+ DPI). "
            "Prioritize extreme typographic clarity and crispness: ensure all small text, stats, borders, card frames, and symbols are sharp and perfectly legible. "
            "Preserve vector-like line art sharpness, vivid color saturation, and dark contrast without blurring edges. Generate at maximum fidelity."
        ),
        input_subpath="trading_card",
        output_subpath="trading_card",
    ),
    ProductType.POKEMON_CARD: ProductProfile(
        product_type=ProductType.POKEMON_CARD,
        display_name="Carta Pokémon Personalizada (TCG 300 DPI)",
        target_dimensions_mm=(63.5, 88.9),
        target_dpi=300,
        aspect_ratio="2.5:3.5 (Standard Pokemon Card)",
        default_orientation="vertical",
        system_prompt=(
            "Generate an authentic official Pokémon Trading Card Game collectible design following strict TCG card anatomy, "
            "Gill Sans/Futura typography, exact elemental energy orbs, and professional 300 DPI micro-print quality."
        ),
        input_subpath="pokemon_card",
        output_subpath="pokemon_card",
    ),
    ProductType.ONEPIECE_CARD: ProductProfile(
        product_type=ProductType.ONEPIECE_CARD,
        display_name="Carta One Piece Card Game (OPCG 300 DPI)",
        target_dimensions_mm=(63.5, 88.9),
        target_dpi=300,
        aspect_ratio="1:1.4 (Trading Card)",
        default_orientation="vertical",
        system_prompt=(
            "Transform this character illustration into an official Bandai One Piece Trading Card Game masterpiece. "
            "Use heavy Shonen typography, official DON!! cost octagon, combat attribute icons, power ratings, "
            "and razor-sharp 300 DPI micro-print quality."
        ),
        input_subpath="onepiece_card",
        output_subpath="onepiece_card",
    ),
    ProductType.CARD_BACK: ProductProfile(
        product_type=ProductType.CARD_BACK,
        display_name="Verso de Carta Colecionável com Sangria (+5mm)",
        target_dimensions_mm=(73.5, 98.9),
        target_dpi=300,
        aspect_ratio="1:1.345 (Card Back Bleed)",
        default_orientation="vertical",
        system_prompt=(
            "Upscale and restore this collectible card back artwork, preserving the central design and ornate frame "
            "completely intact while seamlessly outpainting and extending the background environment by +5mm on all four sides "
            "for industrial print bleed."
        ),
        output_suffix="_bleed_300dpi",
        input_subpath="card_back",
        output_subpath="card_back",
    ),
    ProductType.POLAROID: ProductProfile(
        product_type=ProductType.POLAROID,
        display_name="Foto Estilo Polaroid",
        target_dimensions_mm=(88.0, 107.0),
        target_dpi=300,
        aspect_ratio="1:1.216 (Polaroid)",
        default_orientation="vertical",
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
        default_orientation="horizontal",
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


def find_chrome_executable() -> Optional[Path]:
    """Tenta localizar o executável do Google Chrome instalado no sistema."""
    potential_paths = [
        Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
        Path("C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"),
        Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
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
    fit_mode: str = "pad"  # 'pad', 'blur_pad', 'crop', 'stretch', 'none'
    exact_dimensions: bool = True  # Calibra para os milímetros e DPI exatos do produto


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
    def logs_dir(self) -> Path:
        """Diretório de logs de execução."""
        path = self.data_dir / "logs"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def cdp_url(self) -> str:
        """URL para conexão via Chrome DevTools Protocol."""
        return f"http://127.0.0.1:{self.cdp_port}"
