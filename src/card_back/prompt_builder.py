from pathlib import Path
from typing import Optional, Tuple


class CardBackPromptBuilder:
    """
    Construtor de prompt especializado para versos/fundos de cartas colecionáveis
    com sangria industrial (+5mm em cada lado / +10mm total) e super-resolução.
    """

    @classmethod
    def build_prompt(
        cls,
        image_path: Optional[Path] = None,
        bleed_mm: float = 5.0,
        target_dimensions_mm: Tuple[float, float] = (73.5, 98.9),
    ) -> str:
        w_mm, h_mm = target_dimensions_mm
        return f"""You are an expert prepress printing engineer and master digital artist specializing in collectible Trading Card Games (TCG).

MISSION:
The image in the attachment is an authentic collectible trading card back (fundo / verso de carta). Perform an ultra-high-definition remaster AND seamlessly extend the outer perimeter background outward by +{bleed_mm:.1f} mm on all four sides (+{bleed_mm * 2:.1f} mm total width and height) to create an industrial print bleed margin.

STRICT TECHNICAL SPECIFICATIONS:
- Extended Dimensions with Bleed: {w_mm:.1f} x {h_mm:.1f} mm (Standard 63.5x88.9 mm trading card proportion + {bleed_mm:.1f} mm bleed on left, right, top, and bottom).
- Aspect Ratio: Exactly 1:1.345 vertical/portrait orientation ({w_mm:.1f} mm width by {h_mm:.1f} mm height).
- Resolution: Master 300+ DPI micro-printing definition (~868 x 1168 px), vector-sharp line art and micro-textures, zero compression noise.

COMPOSITION & ZONING RULES:

1. CENTRAL CORE DESIGN PRESERVATION:
   - Keep the original central card illustration, ornate frame/border, emblem, and title typography completely intact, centered, and faithful to the source image in the attachment.
   - Master restoration: upscale every detail with extreme fidelity. Sharpen the lines, enhance ambient glows and lighting, restore fine textures and engravings.
   - Clean up compression artifacts, pixelation, and unwanted corner noise to deliver a pristine collector card back.

2. SEAMLESS PERIMETER BLEED EXPANSION (+{bleed_mm:.1f} mm on all four edges):
   - The existing ornate frame must remain at its standard inner position. DO NOT add a duplicate outer frame.
   - Outpaint and seamlessly expand the ambient background environment beyond the existing frame outward to fill the extra {bleed_mm:.1f} mm margin on all sides.
   - Naturally extend the atmospheric environmental background (lighting, foliage, textures, shadows, and particles) outward seamlessly to all outer edges of the canvas.

STRICT EXCLUSIONS:
- NO 3D perspective tilts, NO table surfaces, NO human hands holding the card.
- NO printer crop marks or cutting registration guidelines.
- Output EXCLUSIVELY the flat 2D rectangular print-ready artwork with seamless outer bleed.
""".strip()
