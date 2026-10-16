"""Esquema de dados e parâmetros para geração de artes de canecas (22x9.5cm @ 300 DPI)."""

import json
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, Field


class MugLayoutType(str, Enum):
    """Tipos de layout para a arte panorâmica da caneca."""
    PHOTO_AND_TEXT = "photo_and_text"      # 1 foto de um lado e bloco de texto/homenagem no outro
    DUO_SIDES = "duo_sides"                # 2 fotos (lado esquerdo e direito da alça)
    TRIO_PHOTOS = "trio_photos"            # 3 fotos (esquerda, centro, direita)
    PANORAMIC_SINGLE = "panoramic_single"  # 1 foto cobrindo todo o wrap ou com fundo esfumaçado
    CUSTOM = "custom"                      # Posicionamento livre configurável


class GradientDirection(str, Enum):
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
    DIAGONAL = "diagonal"


class MugBackgroundConfig(BaseModel):
    """Configuração de fundo do canvas da caneca."""
    color: str = Field(default="#FFFFFF", description="Cor de fundo primária em hex (ex: '#FFFFFF') ou 'auto'.")
    gradient_to: Optional[str] = Field(default=None, description="Cor secundária para degradê em hex (ex: '#E2E8F0').")
    gradient_direction: GradientDirection = Field(default=GradientDirection.HORIZONTAL, description="Direção do degradê.")
    blur_source_photo: bool = Field(default=False, description="Usa a foto principal com desfoque cinematográfico como fundo.")
    blur_intensity: int = Field(default=45, description="Intensidade do desfoque gaussiano se blur_source_photo=True.")
    image_path: Optional[str] = Field(default=None, description="Caminho para uma imagem de estampa/textura de fundo.")
    overlay_opacity: float = Field(default=0.0, description="Opacidade de uma camada translúcida sobre o fundo (0.0 a 1.0).")
    overlay_color: str = Field(default="#000000", description="Cor da camada translúcida.")


class MugPhotoConfig(BaseModel):
    """Configuração de uma foto inserida na caneca."""
    file: str = Field(..., description="Nome do arquivo ou caminho da imagem.")
    position: str = Field(default="left", description="'left', 'right', 'center' ou 'custom'.")
    custom_coords: Optional[Tuple[int, int, int, int]] = Field(
        default=None,
        description="Coordenadas manuais (x, y, largura, altura) em pixels no canvas de 2598x1122."
    )
    border_radius: int = Field(default=28, description="Raio de arredondamento dos cantos em pixels.")
    border_color: str = Field(default="#FFFFFF", description="Cor da moldura/borda em hex.")
    border_width: int = Field(default=12, description="Espessura da borda da foto em pixels (0 para sem borda).")
    shadow: bool = Field(default=True, description="Adiciona sombra suave projetada (drop shadow).")
    shadow_offset: Tuple[int, int] = Field(default=(10, 15), description="Deslocamento (x, y) da sombra.")
    shadow_blur: int = Field(default=25, description="Intensidade do desfoque da sombra.")
    shadow_opacity: float = Field(default=0.35, description="Opacidade da sombra (0.0 a 1.0).")
    aspect_mode: str = Field(default="cover", description="'cover' (preenche cortando bordas) ou 'contain' (mostra inteira).")
    style: str = Field(default="standard", description="'standard' (moldura com cantos arredondados) ou 'polaroid' (foto polaroid clássica).")
    rotation: float = Field(default=0.0, description="Ângulo de rotação/inclinação em graus (ex: -3.5 ou 4.0).")
    caption: Optional[str] = Field(default=None, description="Legenda opcional escrita na base inferior da polaroid.")


class MugTextConfig(BaseModel):
    """Configuração de texto ou mensagem na caneca."""
    title: str = Field(..., description="Texto principal ou frase a ser exibida.")
    subtitle: Optional[str] = Field(default=None, description="Subtítulo, dedicatória ou data.")
    position: str = Field(default="right", description="'right', 'left', 'center' ou 'custom'.")
    custom_coords: Optional[Tuple[int, int]] = Field(default=None, description="Posição manual (x, y) do centro do bloco de texto.")
    font_name: str = Field(default="Segoe UI", description="Nome da fonte instalada (ex: 'Segoe UI', 'Impact', 'Georgia').")
    title_font_size: int = Field(default=68, description="Tamanho da fonte do título principal.")
    subtitle_font_size: int = Field(default=44, description="Tamanho da fonte do subtítulo.")
    title_color: str = Field(default="#1E293B", description="Cor do título em hex.")
    subtitle_color: str = Field(default="#475569", description="Cor do subtítulo em hex.")
    align: str = Field(default="center", description="Alinhamento do texto ('center', 'left', 'right').")
    shadow: bool = Field(default=True, description="Sombra suave sob o texto para maior legibilidade.")
    box_card: bool = Field(default=False, description="Envolve o texto em um card/cartão comemorativo elegante.")
    box_card_color: str = Field(default="#FFFFFFEE", description="Cor de fundo do cartão de texto.")


class MugArtConfig(BaseModel):
    """Configuração completa de uma arte para caneca de 22x9.5cm @ 300 DPI."""
    title: str = Field(default="Arte de Caneca", description="Identificação do projeto/pedido.")
    layout: MugLayoutType = Field(default=MugLayoutType.PHOTO_AND_TEXT, description="Tipo do layout.")
    theme: Optional[str] = Field(default="custom", description="Tema visual (ex: 'professores', 'aniversario', 'casal').")
    background: MugBackgroundConfig = Field(default_factory=MugBackgroundConfig)
    photos: List[MugPhotoConfig] = Field(default_factory=list, description="Lista de fotos a incluir.")
    texts: List[MugTextConfig] = Field(default_factory=list, description="Lista de blocos de texto.")
    ai_prompt_hint: Optional[str] = Field(
        default=None,
        description="Instrução adicional caso a arte seja enviada para processamento pelo Gemini IA."
    )

    @classmethod
    def from_file(cls, path: Union[str, Path]) -> "MugArtConfig":
        """Carrega e valida a configuração a partir de um arquivo JSON."""
        p = Path(path)
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        """Converte a configuração para dicionário serializável."""
        return self.model_dump()

    def save(self, path: Union[str, Path]) -> None:
        """Salva a configuração em um arquivo JSON."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def sample_template(cls, layout: MugLayoutType = MugLayoutType.PHOTO_AND_TEXT) -> "MugArtConfig":
        """Cria um template padrão pronto para uso e edição pelo usuário."""
        if layout == MugLayoutType.PHOTO_AND_TEXT:
            return cls(
                title="Caneca Personalizada",
                layout=MugLayoutType.PHOTO_AND_TEXT,
                theme="comemorativo",
                background=MugBackgroundConfig(
                    color="#F8FAFC",
                    gradient_to="#E2E8F0",
                    gradient_direction=GradientDirection.HORIZONTAL,
                    blur_source_photo=False,
                ),
                photos=[
                    MugPhotoConfig(
                        file="foto.jpg",
                        position="left",
                        border_radius=32,
                        border_color="#FFFFFF",
                        border_width=14,
                        shadow=True,
                    )
                ],
                texts=[
                    MugTextConfig(
                        title="Feliz dia dos professores pra melhor!",
                        subtitle="Prô Glacy ❤️",
                        position="right",
                        title_font_size=64,
                        subtitle_font_size=48,
                        title_color="#0F172A",
                        subtitle_color="#BE185D",
                        align="center",
                        shadow=True,
                        box_card=True,
                    )
                ],
                ai_prompt_hint="Estampa festiva e acolhedora de Dia dos Professores com elementos florais sutis e maçã/livros decorativos."
            )
        elif layout == MugLayoutType.DUO_SIDES:
            return cls(
                title="Caneca 2 Fotos",
                layout=MugLayoutType.DUO_SIDES,
                background=MugBackgroundConfig(color="#FFFFFF"),
                photos=[
                    MugPhotoConfig(file="foto1.jpg", position="left"),
                    MugPhotoConfig(file="foto2.jpg", position="right"),
                ],
                texts=[
                    MugTextConfig(title="Amor Eterno", position="center", title_font_size=56)
                ]
            )
        else:
            return cls(
                title="Caneca Panorâmica",
                layout=MugLayoutType.PANORAMIC_SINGLE,
                background=MugBackgroundConfig(blur_source_photo=True),
                photos=[
                    MugPhotoConfig(file="foto.jpg", position="center", border_width=0, shadow=False)
                ],
                texts=[]
            )
