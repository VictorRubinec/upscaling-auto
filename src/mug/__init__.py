"""Módulo especializado na geração e calibração de artes para canecas de cerâmica (22x9.5cm @ 300 DPI)."""

from src.mug.schema import (
    MugLayoutType,
    MugBackgroundConfig,
    MugPhotoConfig,
    MugTextConfig,
    MugArtConfig,
)
from src.mug.composer import MugComposerEngine
from src.mug.prompt_builder import MugPromptBuilder
from src.mug.manager import MugManager
from src.mug.sublimation import SublimationEngine

__all__ = [
    "MugLayoutType",
    "MugBackgroundConfig",
    "MugPhotoConfig",
    "MugTextConfig",
    "MugArtConfig",
    "MugComposerEngine",
    "MugPromptBuilder",
    "MugManager",
    "SublimationEngine",
]
