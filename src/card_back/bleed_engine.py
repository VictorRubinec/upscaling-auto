from pathlib import Path
from typing import Optional, Tuple, Union
from PIL import Image, ImageDraw, ImageFilter
from src.utils import mm_to_pixels


class CardBleedEngine:
    """
    Motor gráfico de sangria industrial para versos/fundos de cartas (TCG).
    Expande a arte ambiental externa em +N mm (padrão 5.0 mm em cada lado / +10 mm total)
    garantindo que:
    1. A carta central (63.5 x 88.9 mm / 750 x 1050 px a 300 DPI) fique 100% nítida e centrada.
    2. A moldura dourada e elementos visuais nunca sejam cortados pela guilhotina na gráfica.
    3. O perímetro de sangria seja uma continuação contínua e suave da textura de fundo.
    """

    @classmethod
    def detect_safe_strips(cls, img: Image.Image, max_scan: int = 70) -> Tuple[int, int]:
        """
        Detecta automaticamente a margem segura de textura externa antes do início da moldura interna,
        evitando espelhar qualquer detalhe metálico ou decorativo para a sangria.
        """
        gray = img.convert("L")
        w, h = gray.size

        # 1. Varredura no eixo X (borda esquerda)
        diffs_x = []
        for x in range(1, min(max_scan, w // 4)):
            d = sum(abs(gray.getpixel((x, y)) - gray.getpixel((x - 1, y))) for y in range(0, h, max(1, h // 15))) / 15.0
            diffs_x.append((x, d))
        avg_dx = sum(d for _, d in diffs_x) / max(1, len(diffs_x))
        peak_x = max_scan
        for x, d in diffs_x:
            if d > avg_dx * 2.0 and x > 10:
                peak_x = x
                break
        strip_x = max(12, min(30, int(peak_x * 0.65)))

        # 2. Varredura no eixo Y (borda superior)
        diffs_y = []
        for y in range(1, min(max_scan, h // 4)):
            d = sum(abs(gray.getpixel((x, y)) - gray.getpixel((x, y - 1))) for x in range(0, w, max(1, w // 15))) / 15.0
            diffs_y.append((y, d))
        avg_dy = sum(d for _, d in diffs_y) / max(1, len(diffs_y))
        peak_y = max_scan
        for y, d in diffs_y:
            if d > avg_dy * 2.0 and y > 10:
                peak_y = y
                break
        strip_y = max(12, min(35, int(peak_y * 0.65)))

        return strip_x, strip_y

    @classmethod
    def apply_bleed(
        cls,
        image_input: Union[Image.Image, Path, str],
        card_dimensions_mm: Tuple[float, float] = (63.5, 88.9),
        bleed_mm: float = 5.0,
        dpi: int = 300,
        output_path: Optional[Union[Path, str]] = None,
        generate_proof: bool = True,
        strip_x: Optional[int] = None,
        strip_y: Optional[int] = None,
    ) -> Tuple[Image.Image, Optional[Image.Image]]:
        """
        Aplica a sangria industrial contínua sobre a imagem da carta.

        Retorna:
            (bleed_image, proof_image)
        """
        if isinstance(image_input, (str, Path)):
            src_img = Image.open(image_input).convert("RGB")
        else:
            src_img = image_input.convert("RGB")

        # Dimensões nominais do miolo da carta a 300 DPI
        card_w = mm_to_pixels(card_dimensions_mm[0], dpi)
        card_h = mm_to_pixels(card_dimensions_mm[1], dpi)

        # Margem de sangria em pixels
        bleed_px = mm_to_pixels(bleed_mm, dpi)

        # Dimensões totais do canvas de impressão
        total_w = card_w + 2 * bleed_px
        total_h = card_h + 2 * bleed_px

        # Enquadramento do miolo sem barras pretas/leterboxing (Aspect Fill)
        cur_w, cur_h = src_img.size
        scale = max(card_w / cur_w, card_h / cur_h)
        scaled_w = round(cur_w * scale)
        scaled_h = round(cur_h * scale)
        scaled = src_img.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)
        crop_l = (scaled_w - card_w) // 2
        crop_t = (scaled_h - card_h) // 2
        card = scaled.crop((crop_l, crop_t, crop_l + card_w, crop_t + card_h))

        # Determina a profundidade de amostragem de textura
        if strip_x is None or strip_y is None:
            auto_sx, auto_sy = cls.detect_safe_strips(card)
            strip_x = strip_x or auto_sx
            strip_y = strip_y or auto_sy

        # Canvas final
        canvas = Image.new("RGB", (total_w, total_h))

        # 1. Extensão Topo (espelha faixa superior para fora)
        top_strip = (
            card.crop((0, 0, card_w, strip_y))
            .transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            .resize((card_w, bleed_px), Image.Resampling.LANCZOS)
        )
        canvas.paste(top_strip, (bleed_px, 0))

        # 2. Extensão Base (espelha faixa inferior para fora)
        bot_strip = (
            card.crop((0, card_h - strip_y, card_w, card_h))
            .transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            .resize((card_w, bleed_px), Image.Resampling.LANCZOS)
        )
        canvas.paste(bot_strip, (bleed_px, bleed_px + card_h))

        # 3. Extensão Esquerda (espelha faixa esquerda para fora)
        left_strip = (
            card.crop((0, 0, strip_x, card_h))
            .transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            .resize((bleed_px, card_h), Image.Resampling.LANCZOS)
        )
        canvas.paste(left_strip, (0, bleed_px))

        # 4. Extensão Direita (espelha faixa direita para fora)
        right_strip = (
            card.crop((card_w - strip_x, 0, card_w, card_h))
            .transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            .resize((bleed_px, card_h), Image.Resampling.LANCZOS)
        )
        canvas.paste(right_strip, (bleed_px + card_w, bleed_px))

        # 5. Cantos diagonais com mesclagem harmônica
        def make_corner(crop_rect, flip_h, flip_v):
            patch = card.crop(crop_rect)
            if flip_h:
                patch = patch.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            if flip_v:
                patch = patch.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            return patch.resize((bleed_px, bleed_px), Image.Resampling.LANCZOS)

        tl = make_corner((0, 0, strip_x, strip_y), True, True)
        tr = make_corner((card_w - strip_x, 0, card_w, strip_y), True, True)
        bl = make_corner((0, card_h - strip_y, strip_x, card_h), True, True)
        br = make_corner((card_w - strip_x, card_h - strip_y, card_w, card_h), True, True)

        canvas.paste(tl, (0, 0))
        canvas.paste(tr, (bleed_px + card_w, 0))
        canvas.paste(bl, (0, bleed_px + card_h))
        canvas.paste(br, (bleed_px + card_w, bleed_px + card_h))

        # 6. Cola o miolo da carta perfeitamente nítido e centrado
        canvas.paste(card, (bleed_px, bleed_px))

        # 7. Suavização sutil da emenda perimetral (elimina artefatos de borda de 1px)
        seam_mask = Image.new("L", (total_w, total_h), 0)
        draw_mask = ImageDraw.Draw(seam_mask)
        draw_mask.rectangle(
            [bleed_px - 1, bleed_px - 1, bleed_px + card_w + 1, bleed_px + card_h + 1],
            outline=255,
            width=3
        )
        seam_mask = seam_mask.filter(ImageFilter.GaussianBlur(radius=1.2))
        blurred_seam = canvas.filter(ImageFilter.GaussianBlur(radius=1.5))
        canvas = Image.composite(blurred_seam, canvas, seam_mask)

        # 8. Gera imagem de prova de corte técnica (Proof) se solicitado
        proof_img = None
        if generate_proof:
            proof_img = canvas.copy()
            pdraw = ImageDraw.Draw(proof_img)
            # Linha de corte da guilhotina (63.5 x 88.9 mm) em vermelho
            pdraw.rectangle(
                [bleed_px, bleed_px, bleed_px + card_w, bleed_px + card_h],
                outline=(255, 30, 30),
                width=2
            )
            # Margem de segurança interna (3mm dentro do corte = ~35px) em ciano
            safe_margin = mm_to_pixels(3.0, dpi)
            pdraw.rectangle(
                [
                    bleed_px + safe_margin,
                    bleed_px + safe_margin,
                    bleed_px + card_w - safe_margin,
                    bleed_px + card_h - safe_margin,
                ],
                outline=(0, 200, 255),
                width=1
            )

        # 9. Salva arquivos no disco se especificado
        if output_path:
            out_p = Path(output_path)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            canvas.save(str(out_p), format="PNG", dpi=(dpi, dpi))

            if proof_img:
                proof_p = out_p.with_name(f"{out_p.stem}_proof.png")
                proof_img.save(str(proof_p), format="PNG", dpi=(dpi, dpi))

        return canvas, proof_img
