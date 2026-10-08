import json
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class OpColor(str, Enum):
    """Cores oficiais das facções de One Piece Card Game."""
    RED = "Red"
    GREEN = "Green"
    BLUE = "Blue"
    PURPLE = "Purple"
    BLACK = "Black"
    YELLOW = "Yellow"
    MULTI = "Multi"


class CardCategory(str, Enum):
    """Categorias estruturais de cartas de One Piece."""
    LEADER = "Leader"
    CHARACTER = "Character"
    EVENT = "Event"
    STAGE = "Stage"


class AttributeType(str, Enum):
    """Atributos de combate oficiais."""
    SLASH = "Slash"
    STRIKE = "Strike"
    RANGED = "Ranged"
    SPECIAL = "Special"
    WISDOM = "Wisdom"


class OpCardStyle(str, Enum):
    """Estilos visuais e raridades de acabamento de One Piece TCG."""
    STANDARD = "standard"            # Borda e moldura oficial padrão (Common / Rare)
    EXTENDED = "extended"            # Parallel Art / Winner (Arte estendida rompendo a moldura)
    MANGA_ALT_ART = "manga_alt_art"  # Super Parallel / Manga Rare (Painéis de mangá P&B ao fundo + personagem 3D em cores)


class OpRarity(str, Enum):
    """Raridades oficiais."""
    L = "L"      # Leader
    C = "C"      # Common
    UC = "UC"    # Uncommon
    R = "R"      # Rare
    SR = "SR"    # Super Rare
    SEC = "SEC"  # Secret Rare
    SP = "SP"    # Special Parallel


class OnePieceCardData(BaseModel):
    """Modelo canônico de dados para geração de cartas oficiais de One Piece TCG."""
    name: str = Field(..., description="Nome oficial do personagem ou carta (ex: 'Monkey D. Luffy', 'Roronoa Zoro')")
    category: CardCategory = Field(default=CardCategory.CHARACTER, description="Categoria da carta (Leader, Character, Event, Stage)")
    color: OpColor = Field(default=OpColor.RED, description="Cor primária da facção")
    secondary_color: Optional[OpColor] = Field(default=None, description="Segunda cor (para Líderes bicolores)")
    
    # Atributos de Custo e Combate
    cost: Optional[int] = Field(default=5, description="Custo em DON!! (1 a 10). Opcional em Líderes.")
    life: Optional[int] = Field(default=None, description="Vida inicial do Líder (normalmente 4 ou 5). Apenas para Leaders.")
    power: Optional[int] = Field(default=6000, description="Poder de ataque (ex: 5000, 6000, 7000). None para Event/Stage.")
    counter: Optional[int] = Field(default=1000, description="Poder de contra-ataque (+1000, +2000). None para Leader/Event/Stage.")
    attribute: Optional[AttributeType] = Field(default=AttributeType.STRIKE, description="Atributo de combate (Slash, Strike, etc.)")
    
    # Afiliações e Efeitos
    affiliations: List[str] = Field(default_factory=lambda: ["Straw Hat Crew"], description="Tribo ou bando pirata (ex: ['Supernovas', 'Straw Hat Crew'])")
    effect: str = Field(..., description="Texto oficial de regras com tags como [DON!! x1], [On Play], [When Attacking]")
    trigger: Optional[str] = Field(default=None, description="Efeito de Trigger ativado na quebra de Vida (faixa dourada)")
    
    # Metadados e Colecionismo
    card_code: str = Field(default="OP05-001", description="Código de expansão e número (ex: 'OP05-119')")
    rarity: OpRarity = Field(default=OpRarity.SR, description="Raridade oficial (L, C, UC, R, SR, SEC, SP)")
    style: OpCardStyle = Field(default=OpCardStyle.MANGA_ALT_ART, description="Estilo visual (standard, extended, manga_alt_art)")
    illustrator: str = Field(default="Studio Kustom", description="Crédito de arte no rodapé")
    flavor_quote: Optional[str] = Field(default=None, description="Citação dramática ou fala icônica do personagem")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OnePieceCardData":
        """Carrega e normaliza valores de dicionário tratando enums de forma tolerante."""
        d = dict(data)
        
        # Normalização de Cor
        if "color" in d and isinstance(d["color"], str):
            for c in OpColor:
                if c.value.lower() == d["color"].lower():
                    d["color"] = c
                    break
        if "secondary_color" in d and isinstance(d["secondary_color"], str):
            for c in OpColor:
                if c.value.lower() == d["secondary_color"].lower():
                    d["secondary_color"] = c
                    break

        # Normalização de Categoria
        if "category" in d and isinstance(d["category"], str):
            for cat in CardCategory:
                if cat.value.lower() == d["category"].lower():
                    d["category"] = cat
                    break

        # Normalização de Atributo
        if "attribute" in d and isinstance(d["attribute"], str):
            for attr in AttributeType:
                if attr.value.lower() == d["attribute"].lower():
                    d["attribute"] = attr
                    break

        # Normalização de Estilo
        if "style" in d and isinstance(d["style"], str):
            for s in OpCardStyle:
                if s.value.lower() == d["style"].lower():
                    d["style"] = s
                    break

        # Normalização de Raridade
        if "rarity" in d and isinstance(d["rarity"], str):
            for r in OpRarity:
                if r.value.lower() == d["rarity"].lower():
                    d["rarity"] = r
                    break

        # Normalização de Afiliações
        if "affiliations" in d and isinstance(d["affiliations"], str):
            d["affiliations"] = [a.strip() for a in d["affiliations"].split("/") if a.strip()]

        return cls(**d)
