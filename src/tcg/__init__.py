"""
Módulo unificado de Trading Card Games (TCGs) para o pipeline upscaling-auto.
Suporta One Piece Card Game (OPCG), Pokémon TCG, Magic: The Gathering (MTG),
Yu-Gi-Oh! (YGO) e Cartas Genéricas/Customizadas.
"""
from src.tcg.onepiece import (
    OnePieceCardData,
    OpColor,
    CardCategory,
    AttributeType,
    OpCardStyle,
    OpRarity,
    OnePiecePromptBuilder,
    OnePieceCardManager,
)

__all__ = [
    "OnePieceCardData",
    "OpColor",
    "CardCategory",
    "AttributeType",
    "OpCardStyle",
    "OpRarity",
    "OnePiecePromptBuilder",
    "OnePieceCardManager",
]
