import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from PIL import Image
from src.card_back.bleed_engine import CardBleedEngine
from src.utils import mm_to_pixels


def test_card_bleed_dimensions():
    # Cria uma imagem de teste sintética
    test_img = Image.new("RGB", (750, 1050), color=(20, 40, 20))
    bleed_img, proof_img = CardBleedEngine.apply_bleed(
        test_img,
        card_dimensions_mm=(63.5, 88.9),
        bleed_mm=5.0,
        dpi=300,
        generate_proof=True,
    )

    expected_w = mm_to_pixels(73.5, 300) # 868
    expected_h = mm_to_pixels(98.9, 300) # 1168

    assert bleed_img.size == (expected_w, expected_h), f"Esperado {(expected_w, expected_h)}, obtido {bleed_img.size}"
    assert proof_img is not None
    assert proof_img.size == (expected_w, expected_h)
    print(f"[OK] Teste de dimensões de sangria passou com sucesso! {bleed_img.size}")


def test_strip_detection():
    # Cria uma imagem com borda escura e centro claro
    test_img = Image.new("RGB", (750, 1050), color=(15, 15, 15))
    for y in range(40, 1010):
        for x in range(35, 715):
            test_img.putpixel((x, y), (200, 180, 50))

    sx, sy = CardBleedEngine.detect_safe_strips(test_img)
    assert 12 <= sx <= 30, f"strip_x fora do limite seguro: {sx}"
    assert 12 <= sy <= 35, f"strip_y fora do limite seguro: {sy}"
    print(f"[OK] Teste de detecção de faixas de segurança passou! strip_x={sx}, strip_y={sy}")


if __name__ == "__main__":
    test_card_bleed_dimensions()
    test_strip_detection()
