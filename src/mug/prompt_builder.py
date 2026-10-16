"""Construtor de prompts especializados para geração de artes de canecas via IA (Gemini)."""

from pathlib import Path
from typing import Optional
from src.mug.schema import MugArtConfig, MugLayoutType


class MugPromptBuilder:
    """Gera prompts refinados para o Gemini no formato panorâmico de canecas de cerâmica."""

    @classmethod
    def build_prompt_for_image(
        cls,
        image_path: Path,
        config: Optional[MugArtConfig] = None,
        logger=None
    ) -> str:
        """Constrói um prompt customizado com base nos parâmetros da arte ou dados inferidos."""
        if config:
            return cls.build_prompt_from_config(config)

        parent = image_path.parent
        candidates = [
            parent / f"{image_path.stem}.json",
            parent / "config.json",
            parent / "mug.json",
        ]
        for c in candidates:
            if c.exists():
                try:
                    cfg = MugArtConfig.from_file(c)
                    if logger:
                        logger.info(f"☕ [Mug Prompt] Parâmetros carregados de: {c.name}")
                    return cls.build_prompt_from_config(cfg)
                except Exception:
                    pass

        return (
            "Create an ultra-high-definition panoramic ceramic mug wrap artwork (dimensions: 220x95mm at 300 DPI, 2598x1122 pixels). "
            "Set on a clean, solid pure white background (#FFFFFF). "
            "On one side, showcase the provided portrait photo seamlessly inside a tilted vintage Polaroid instant photo frame with realistic paper border and subtle soft drop shadow. "
            "On the other side, display large, expressive handwritten script lettering in Brazilian Portuguese: "
            "'Feliz dia dos professores pra melhor! Prô Glacy ❤️' "
            "with a cute bright red heart symbol. "
            "Maintain strict 22:9.5 panoramic horizontal orientation calibrated for physical mug sublimation print."
        )

    @classmethod
    def build_prompt_from_config(cls, cfg: MugArtConfig) -> str:
        """Gera prompt detalhado a partir de uma ficha de configuração completa."""
        # Se houver um prompt personalizado explícito configurado
        if cfg.ai_prompt_hint and len(cfg.ai_prompt_hint.strip()) > 30:
            return (
                f"Create an ultra-high-definition panoramic ceramic coffee mug wrap artwork (dimensions: exact 220x95mm at 300 DPI, wide 22:9.5 aspect ratio, 2598x1122 pixels). "
                f"{cfg.ai_prompt_hint.strip()} "
                f"Ensure the physical dimensions are flat, horizontal 22x9.5cm calibrated for physical ceramic heat sublimation printing without distortion. Output maximum resolution."
            )

        bg_desc = "solid pure white background (#FFFFFF)" if cfg.background.color.upper() == "#FFFFFF" else f"clean background with color {cfg.background.color}"

        text_lines = []
        for t in cfg.texts:
            text_lines.append(t.title)
            if t.subtitle:
                text_lines.append(t.subtitle)
        text_str = " \n ".join(text_lines) if text_lines else ""

        text_clause = f"Display the text clearly: '{text_str}'. " if text_str else ""

        return (
            f"Generate an ultra-high-definition panoramic ceramic mug sublimation print wrap (dimensions: 220x95mm at 300 DPI, exact 22:9.5 wide aspect ratio, 2598x1122 pixels). "
            f"Background: Crisp, minimalist {bg_desc}. "
            f"Composition: "
            f"1. On the left side, feature an expressive artistic portrait based on the left photo. "
            f"2. On the right side, feature an expressive artistic portrait based on the right photo. "
            f"{text_clause}"
            f"Keep the entire layout clean, loving, and balanced with generous negative space. "
            f"Strictly horizontal flat wrap format for dye-sublimation ceramic mug transfer. Deliver in maximum resolution."
        )
