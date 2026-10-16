"""Script de execução para gerar os 5 modelos de montagem e salvá-los em data/output/mug/ e nos artefatos."""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from pathlib import Path
from PIL import Image

from src.mug.style_generator import (
    generate_style_1_editorial,
    generate_style_2_boho_arch,
    generate_style_3_scrapbook,
    generate_style_4_spotify,
    generate_style_5_film_strip,
    DPI
)

def run():
    in_dir = Path("data/input/mug")
    out_dir = Path("data/output/mug")
    art_dir = Path(r"C:/Users/Rubinec/.gemini/antigravity/brain/1cdd5f7f-ff9f-47f3-9144-777b28e7dfe1")
    out_dir.mkdir(parents=True, exist_ok=True)

    img_casal = Image.open(in_dir / "casal_polaroid.png")
    img_familia = Image.open(in_dir / "familia_polaroid.jpg")

    generators = [
        ("estilo_1_editorial_clean", generate_style_1_editorial),
        ("estilo_2_arcos_boho", generate_style_2_boho_arch),
        ("estilo_3_scrapbook_washi", generate_style_3_scrapbook),
        ("estilo_4_spotify_player", generate_style_4_spotify),
        ("estilo_5_filme_retro", generate_style_5_film_strip),
    ]

    for name, gen_fn in generators:
        canvas = gen_fn(img_casal, img_familia)
        target_png = out_dir / f"{name}_22x9.5cm_300dpi.png"
        canvas.save(target_png, "PNG", dpi=(DPI, DPI))

        # Copia para artefatos
        art_png = art_dir / f"{name}.png"
        canvas.save(art_png, "PNG", dpi=(DPI, DPI))
        print(f"✅ Gerado com sucesso: {name} -> {target_png.name} ({canvas.size} @ {DPI} DPI)")

if __name__ == "__main__":
    run()
