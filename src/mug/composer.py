"""Motor gráfico de composição e diagramação para artes de canecas (22x9.5cm @ 300 DPI)."""

from pathlib import Path
from typing import List, Optional, Tuple, Union
import math
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from src.mug.schema import (
    GradientDirection,
    MugArtConfig,
    MugBackgroundConfig,
    MugLayoutType,
    MugPhotoConfig,
    MugTextConfig,
)
from src.utils import mm_to_pixels


def hex_to_rgb(hex_code: str) -> Tuple[int, int, int]:
    """Converte cor em formato hexadecimal para tupla RGB."""
    hex_code = hex_code.strip().lstrip("#")
    if len(hex_code) == 3:
        hex_code = "".join([c * 2 for c in hex_code])
    if len(hex_code) == 6:
        return int(hex_code[0:2], 16), int(hex_code[2:4], 16), int(hex_code[4:6], 16)
    if len(hex_code) == 8:
        return int(hex_code[0:2], 16), int(hex_code[2:4], 16), int(hex_code[4:6], 16)
    return (255, 255, 255)


def get_system_font(font_name: str, size: int) -> ImageFont.FreeTypeFont:
    """Tenta localizar e carregar a fonte especificada no sistema Windows com fallback inteligente."""
    windows_fonts = Path("C:/Windows/Fonts")
    font_map = {
        "segoe ui": "segoeui.ttf",
        "segoe ui bold": "segoeuib.ttf",
        "segoe print": "segoepr.ttf",
        "segoe script": "segoesc.ttf",
        "arial": "arial.ttf",
        "arial bold": "arialbd.ttf",
        "georgia": "georgia.ttf",
        "georgia bold": "georgiab.ttf",
        "impact": "impact.ttf",
        "calibri": "calibri.ttf",
        "calibri bold": "calibrib.ttf",
        "trebuchet ms": "trebuc.ttf",
    }

    cleaned = font_name.lower().strip()
    font_filename = font_map.get(cleaned, font_name if font_name.endswith((".ttf", ".otf")) else f"{cleaned}.ttf")
    font_path = windows_fonts / font_filename

    if font_path.exists():
        try:
            return ImageFont.truetype(str(font_path), size)
        except Exception:
            pass

    # Fallbacks comuns de alta qualidade
    for fallback in ["segoeuib.ttf", "arialbd.ttf", "georgiab.ttf", "calibrib.ttf", "arial.ttf"]:
        fb_path = windows_fonts / fallback
        if fb_path.exists():
            try:
                return ImageFont.truetype(str(fb_path), size)
            except Exception:
                pass

    return ImageFont.load_default()


class MugComposerEngine:
    """Motor de composição e diagramação visual para canecas de cerâmica padrão 22x9.5cm a 300 DPI."""

    CANVAS_WIDTH_MM = 220.0
    CANVAS_HEIGHT_MM = 95.0
    DPI = 300

    TARGET_WIDTH_PX = 2598   # round(220 * 300 / 25.4)
    TARGET_HEIGHT_PX = 1122  # round(95 * 300 / 25.4)

    @classmethod
    def render_art(
        cls,
        config: MugArtConfig,
        base_dir: Optional[Path] = None,
        generate_proof: bool = True
    ) -> Tuple[Image.Image, Optional[Image.Image]]:
        """
        Gera a arte completa da caneca nas medidas exatas de 22x9.5cm a 300 DPI.
        Retorna a tupla (imagem_final, imagem_com_guias_de_corte).
        """
        canvas = cls._render_background(config, base_dir)

        # 1. Renderiza as fotos
        cls._render_photos(canvas, config, base_dir)

        # 2. Renderiza os textos e cartões
        cls._render_texts(canvas, config)

        final_img = canvas.convert("RGB")

        proof_img = None
        if generate_proof:
            proof_img = cls._create_proof_sheet(final_img)

        return final_img, proof_img

    @classmethod
    def _render_background(cls, config: MugArtConfig, base_dir: Optional[Path]) -> Image.Image:
        """Gera a camada de fundo da arte."""
        w, h = cls.TARGET_WIDTH_PX, cls.TARGET_HEIGHT_PX
        bg_cfg = config.background

        # Caso 1: Fundo desfocado cinematográfico a partir da primeira foto
        if bg_cfg.blur_source_photo and config.photos:
            first_photo_path = cls._resolve_path(config.photos[0].file, base_dir)
            if first_photo_path and first_photo_path.exists():
                try:
                    with Image.open(first_photo_path) as p_img:
                        p_rgb = p_img.convert("RGB")
                        # Cover canvas
                        scale = max(w / p_rgb.width, h / p_rgb.height)
                        sw, sh = round(p_rgb.width * scale), round(p_rgb.height * scale)
                        resized = p_rgb.resize((sw, sh), Image.Resampling.BILINEAR)
                        left = (sw - w) // 2
                        top = (sh - h) // 2
                        cropped = resized.crop((left, top, left + w, top + h))
                        bg = cropped.filter(ImageFilter.GaussianBlur(radius=bg_cfg.blur_intensity))

                        # Aplica camada de overlay suave se configurada
                        if bg_cfg.overlay_opacity > 0:
                            overlay = Image.new("RGBA", (w, h), hex_to_rgb(bg_cfg.overlay_color) + (int(255 * bg_cfg.overlay_opacity),))
                            bg_rgba = bg.convert("RGBA")
                            bg = Image.alpha_composite(bg_rgba, overlay).convert("RGB")
                        return bg
                except Exception:
                    pass

        # Caso 2: Imagem/Estampa de textura externa fornecida
        if bg_cfg.image_path:
            bg_path = cls._resolve_path(bg_cfg.image_path, base_dir)
            if bg_path and bg_path.exists():
                try:
                    with Image.open(bg_path) as b_img:
                        b_rgb = b_img.convert("RGB")
                        scale = max(w / b_rgb.width, h / b_rgb.height)
                        sw, sh = round(b_rgb.width * scale), round(b_rgb.height * scale)
                        resized = b_rgb.resize((sw, sh), Image.Resampling.LANCZOS)
                        left = (sw - w) // 2
                        top = (sh - h) // 2
                        return resized.crop((left, top, left + w, top + h))
                except Exception:
                    pass

        # Caso 3: Degradê linear suave
        if bg_cfg.gradient_to:
            c1 = hex_to_rgb(bg_cfg.color)
            c2 = hex_to_rgb(bg_cfg.gradient_to)
            grad_img = Image.new("RGB", (w, h))
            draw = ImageDraw.Draw(grad_img)

            if bg_cfg.gradient_direction == GradientDirection.HORIZONTAL:
                for x in range(w):
                    t = x / max(1, w - 1)
                    r = int(c1[0] * (1 - t) + c2[0] * t)
                    g = int(c1[1] * (1 - t) + c2[1] * t)
                    b = int(c1[2] * (1 - t) + c2[2] * t)
                    draw.line([(x, 0), (x, h)], fill=(r, g, b))
            else:  # VERTICAL
                for y in range(h):
                    t = y / max(1, h - 1)
                    r = int(c1[0] * (1 - t) + c2[0] * t)
                    g = int(c1[1] * (1 - t) + c2[1] * t)
                    b = int(c1[2] * (1 - t) + c2[2] * t)
                    draw.line([(0, y), (w, y)], fill=(r, g, b))
            return grad_img

        # Caso 4: Cor sólida
        primary_color = hex_to_rgb(bg_cfg.color)
        return Image.new("RGB", (w, h), color=primary_color)

    @classmethod
    def _render_photos(cls, canvas: Image.Image, config: MugArtConfig, base_dir: Optional[Path]) -> None:
        """Renderiza cada foto nas posições do layout correspondente com bordas, arredondamento e sombra."""
        if not config.photos:
            return

        w, h = cls.TARGET_WIDTH_PX, cls.TARGET_HEIGHT_PX

        # Determina caixas padrão para cada posição do layout
        # Margem de segurança da alça: ~140px nas bordas esquerda e direita
        safe_margin_x = 140
        safe_margin_y = 70
        usable_height = h - (safe_margin_y * 2)

        boxes = cls._calculate_layout_boxes(config, w, h, safe_margin_x, safe_margin_y, usable_height)

        for idx, photo_cfg in enumerate(config.photos):
            photo_path = cls._resolve_path(photo_cfg.file, base_dir)
            if not photo_path or not photo_path.exists():
                continue

            target_box = photo_cfg.custom_coords or boxes.get(photo_cfg.position.lower(), boxes.get(f"slot_{idx}", (safe_margin_x, safe_margin_y, 900, usable_height)))
            bx, by, bw, bh = target_box

            cls._paste_styled_photo(canvas, photo_path, bx, by, bw, bh, photo_cfg)

    @classmethod
    def _calculate_layout_boxes(cls, config: MugArtConfig, w: int, h: int, margin_x: int, margin_y: int, usable_h: int) -> dict:
        """Calcula posições de caixas harmônicas de acordo com o tipo de layout."""
        layout = config.layout
        boxes = {}

        if layout == MugLayoutType.PHOTO_AND_TEXT:
            # Foto ocupando um lado da caneca (proporção agradável tipo retrato 880x980 px)
            pw = 880
            ph = min(usable_h, 980)
            py = (h - ph) // 2

            # Left side: centro em ~650 px
            left_px = margin_x + ((w // 2 - margin_x) - pw) // 2
            boxes["left"] = (left_px, py, pw, ph)

            # Right side: centro em ~1948 px
            right_px = (w // 2) + ((w // 2 - margin_x) - pw) // 2
            boxes["right"] = (right_px, py, pw, ph)

            # Center
            boxes["center"] = ((w - pw) // 2, py, pw, ph)

        elif layout == MugLayoutType.DUO_SIDES:
            pw = 840
            ph = min(usable_h, 960)
            py = (h - ph) // 2

            left_px = margin_x + ((w // 2 - margin_x) - pw) // 2
            right_px = (w // 2) + ((w // 2 - margin_x) - pw) // 2
            boxes["left"] = (left_px, py, pw, ph)
            boxes["right"] = (right_px, py, pw, ph)
            boxes["slot_0"] = boxes["left"]
            boxes["slot_1"] = boxes["right"]

        elif layout == MugLayoutType.TRIO_PHOTOS:
            pw = 680
            ph = min(usable_h, 920)
            py = (h - ph) // 2
            gap = 60

            total_w = (pw * 3) + (gap * 2)
            start_x = (w - total_w) // 2

            boxes["left"] = (start_x, py, pw, ph)
            boxes["center"] = (start_x + pw + gap, py, pw, ph)
            boxes["right"] = (start_x + (pw + gap) * 2, py, pw, ph)
            boxes["slot_0"] = boxes["left"]
            boxes["slot_1"] = boxes["center"]
            boxes["slot_2"] = boxes["right"]

        else:  # PANORAMIC_SINGLE
            pw = w - (margin_x * 2)
            ph = usable_h
            boxes["center"] = (margin_x, margin_y, pw, ph)
            boxes["left"] = (margin_x, margin_y, pw, ph)

        return boxes

    @classmethod
    def _prepare_source_photo(cls, src_img: Image.Image) -> Image.Image:
        """
        Ajusta previamente a foto do cliente para sublimação e casamento com Perfil ICC:
        1. Corrige balanço de branco se a foto tiver tom frio/azulado (típico de celulares e luz artificial).
        2. Aplica leve reforço de vitalidade nos tons de pele para que não fiquem desbotados na caneca.
        """
        from PIL import ImageEnhance, ImageStat
        rgb = src_img.convert("RGB")
        stat = ImageStat.Stat(rgb)
        mean_r, mean_g, mean_b = stat.mean[0], stat.mean[1], stat.mean[2]

        # Se houver predominância fria (canal B ou G maior que R)
        if mean_b > mean_r or mean_g > mean_r:
            r, g, b = rgb.split()
            r = r.point(lambda i: min(255, int(i * 1.04)))
            b = b.point(lambda i: int(i * 0.96))
            rgb = Image.merge("RGB", (r, g, b))

        # Leve reforço de saturação e contraste para imagem de entrada
        sat_enhancer = ImageEnhance.Color(rgb)
        rgb = sat_enhancer.enhance(1.06)

        con_enhancer = ImageEnhance.Contrast(rgb)
        rgb = con_enhancer.enhance(1.04)

        return rgb.convert("RGBA")

    @classmethod
    def _paste_styled_photo(
        cls,
        canvas: Image.Image,
        photo_path: Path,
        x: int,
        y: int,
        box_w: int,
        box_h: int,
        cfg: MugPhotoConfig
    ) -> None:
        """Aplica redimensionamento proporcional, borda, cantos arredondados e sombra na foto."""
        try:
            if cfg.style == "polaroid":
                cx = x + (box_w // 2)
                cy = y + (box_h // 2)
                cls._paste_polaroid_photo(canvas, photo_path, cx, cy, cfg)
                return

            with Image.open(photo_path) as raw_img:
                src_rgb = cls._prepare_source_photo(raw_img)

                # Recorte proporcional para preencher box_w x box_h (Cover)
                scale = max(box_w / src_rgb.width, box_h / src_rgb.height)
                sw, sh = round(src_rgb.width * scale), round(src_rgb.height * scale)
                resized = src_rgb.resize((sw, sh), Image.Resampling.LANCZOS)

                cx = (sw - box_w) // 2
                cy = (sh - box_h) // 2
                photo_cropped = resized.crop((cx, cy, cx + box_w, cy + box_h))

                # Cria máscara para cantos arredondados (supersampling 2x para nitidez perfeita)
                ss = 2
                mask_large = Image.new("L", (box_w * ss, box_h * ss), 0)
                mask_draw = ImageDraw.Draw(mask_large)
                mask_draw.rounded_rectangle(
                    [(0, 0), (box_w * ss, box_h * ss)],
                    radius=cfg.border_radius * ss,
                    fill=255
                )
                mask = mask_large.resize((box_w, box_h), Image.Resampling.LANCZOS)

                # Se houver borda
                framed_w = box_w
                framed_h = box_h
                framed_img = Image.new("RGBA", (framed_w, framed_h), (0, 0, 0, 0))

                # Desenha a foto com a máscara
                framed_img.paste(photo_cropped, (0, 0), mask=mask)

                if cfg.border_width > 0:
                    border_mask_large = Image.new("RGBA", (box_w * ss, box_h * ss), (0, 0, 0, 0))
                    bdraw = ImageDraw.Draw(border_mask_large)
                    b_color = hex_to_rgb(cfg.border_color) + (255,)
                    bdraw.rounded_rectangle(
                        [(0, 0), (box_w * ss, box_h * ss)],
                        radius=cfg.border_radius * ss,
                        outline=b_color,
                        width=cfg.border_width * ss
                    )
                    border_img = border_mask_large.resize((box_w, box_h), Image.Resampling.LANCZOS)
                    framed_img = Image.alpha_composite(framed_img, border_img)

                # Renderiza Drop Shadow suave
                if cfg.shadow:
                    pad = cfg.shadow_blur * 2
                    shadow_img = Image.new(
                        "RGBA",
                        (framed_w + pad * 2, framed_h + pad * 2),
                        (0, 0, 0, 0)
                    )
                    sdraw = ImageDraw.Draw(shadow_img)
                    s_alpha = int(255 * cfg.shadow_opacity)
                    sdraw.rounded_rectangle(
                        [(pad, pad), (pad + framed_w, pad + framed_h)],
                        radius=cfg.border_radius,
                        fill=(15, 23, 42, s_alpha)
                    )
                    shadow_blurred = shadow_img.filter(ImageFilter.GaussianBlur(radius=cfg.shadow_blur))

                    sx = x + cfg.shadow_offset[0] - pad
                    sy = y + cfg.shadow_offset[1] - pad

                    canvas_rgba = canvas.convert("RGBA")
                    canvas_rgba.alpha_composite(shadow_blurred, (sx, sy))
                    canvas_rgba.alpha_composite(framed_img, (x, y))
                    canvas.paste(canvas_rgba.convert("RGB"), (0, 0))
                else:
                    canvas_rgba = canvas.convert("RGBA")
                    canvas_rgba.alpha_composite(framed_img, (x, y))
                    canvas.paste(canvas_rgba.convert("RGB"), (0, 0))

        except Exception as e:
            pass

    @classmethod
    def _paste_polaroid_photo(
        cls,
        canvas: Image.Image,
        photo_path: Path,
        center_x: int,
        center_y: int,
        cfg: MugPhotoConfig
    ) -> None:
        """Renderiza uma foto no formato Polaroid autêntico, com inclinação angular e sombra realista."""
        try:
            with Image.open(photo_path) as raw_img:
                src_rgb = cls._prepare_source_photo(raw_img)

                # Dimensões da moldura Polaroid clássica em pixels a 300 DPI
                frame_w = 780
                frame_h = 950
                margin_side = 48
                margin_top = 48
                margin_bottom = 160

                photo_w = frame_w - (margin_side * 2)  # 684 px
                photo_h = frame_h - margin_top - margin_bottom  # 742 px

                # Recorte proporcional para preencher a janela da Polaroid (Aspect Fill)
                scale = max(photo_w / src_rgb.width, photo_h / src_rgb.height)
                sw, sh = round(src_rgb.width * scale), round(src_rgb.height * scale)
                resized = src_rgb.resize((sw, sh), Image.Resampling.LANCZOS)
                cx = (sw - photo_w) // 2
                cy = (sh - photo_h) // 2
                photo_cropped = resized.crop((cx, cy, cx + photo_w, cy + photo_h))

                # Cria o cartão da Polaroid com papel fotográfico texturizado off-white
                card = Image.new("RGBA", (frame_w, frame_h), (252, 252, 250, 255))
                cdraw = ImageDraw.Draw(card)
                cdraw.rounded_rectangle(
                    [(0, 0), (frame_w, frame_h)],
                    radius=14,
                    fill=(254, 254, 252, 255),
                    outline=(226, 232, 240, 255),
                    width=2
                )
                card.paste(photo_cropped, (margin_side, margin_top))

                # Borda interna finíssima de recorte de papel ao redor da foto
                cdraw.rectangle(
                    [(margin_side, margin_top), (margin_side + photo_w, margin_top + photo_h)],
                    outline=(203, 213, 225, 200),
                    width=2
                )

                # Legenda opcional na base da polaroid
                if cfg.caption:
                    cap_font = get_system_font("Segoe Print", 38)
                    c_bbox = cdraw.textbbox((0, 0), cfg.caption, font=cap_font)
                    cap_w = c_bbox[2] - c_bbox[0]
                    cap_x = (frame_w - cap_w) // 2
                    cap_y = margin_top + photo_h + ((margin_bottom - (c_bbox[3] - c_bbox[1])) // 2) - 8
                    cdraw.text((cap_x, cap_y), cfg.caption, font=cap_font, fill=(51, 65, 85, 255))

                # Rotação suave se especificada (ex: -3.5° ou +3.5°)
                rot_angle = cfg.rotation
                if rot_angle != 0.0:
                    card_rot = card.rotate(-rot_angle, resample=Image.Resampling.BICUBIC, expand=True)
                else:
                    card_rot = card

                # Criação da sombra projetada realista sob a polaroid
                rw, rh = card_rot.size
                pad = 55
                shadow_canvas = Image.new("RGBA", (rw + pad * 2, rh + pad * 2), (0, 0, 0, 0))
                shadow_mask = card_rot.split()[3]
                shadow_silhouette = Image.new("RGBA", (rw, rh), (15, 23, 42, int(255 * cfg.shadow_opacity)))
                shadow_canvas.paste(shadow_silhouette, (pad, pad), mask=shadow_mask)
                shadow_blurred = shadow_canvas.filter(ImageFilter.GaussianBlur(radius=cfg.shadow_blur))

                # Posiciona no canvas principal centralizado em (center_x, center_y)
                paste_x = center_x - (rw // 2)
                paste_y = center_y - (rh // 2)

                canvas_rgba = canvas.convert("RGBA")
                canvas_rgba.alpha_composite(shadow_blurred, (paste_x - pad + 8, paste_y - pad + 14))
                canvas_rgba.alpha_composite(card_rot, (paste_x, paste_y))
                canvas.paste(canvas_rgba.convert("RGB"), (0, 0))
        except Exception:
            pass

    @classmethod
    def _render_texts(cls, canvas: Image.Image, config: MugArtConfig) -> None:
        """Renderiza os blocos de texto, tipografia decorada e símbolos comemorativos."""
        if not config.texts:
            return

        w, h = cls.TARGET_WIDTH_PX, cls.TARGET_HEIGHT_PX
        safe_margin_x = 140

        for txt_cfg in config.texts:
            # Determina o centro de ancoragem do bloco de texto
            if txt_cfg.custom_coords:
                center_x, center_y = txt_cfg.custom_coords
            elif txt_cfg.position == "left":
                center_x = safe_margin_x + (w // 4)
                center_y = h // 2
            elif txt_cfg.position == "center":
                center_x = w // 2
                center_y = h // 2
            else:  # right (padrão em photo_and_text)
                center_x = (w // 2) + ((w // 2 - safe_margin_x) // 2)
                center_y = h // 2

            cls._render_single_text_block(canvas, txt_cfg, center_x, center_y)

    @classmethod
    def _render_single_text_block(cls, canvas: Image.Image, cfg: MugTextConfig, cx: int, cy: int) -> None:
        """Desenha título, subtítulo e opcionalmente cartão comemorativo de fundo."""
        title_font = get_system_font(f"{cfg.font_name} Bold", cfg.title_font_size)
        sub_font = get_system_font(cfg.font_name, cfg.subtitle_font_size)

        title_lines = cls._wrap_text(cfg.title, title_font, max_width=920)
        sub_lines = cls._wrap_text(cfg.subtitle or "", sub_font, max_width=920) if cfg.subtitle else []

        line_spacing = 24
        total_text_h = 0
        draw_temp = ImageDraw.Draw(canvas)

        # Calcula a altura total de cada linha
        line_heights = []
        for l in title_lines:
            bbox = draw_temp.textbbox((0, 0), l, font=title_font)
            lh = bbox[3] - bbox[1]
            line_heights.append((l, title_font, lh, cfg.title_color, True))
            total_text_h += lh + line_spacing

        if sub_lines:
            total_text_h += 30  # Gap extra entre título e subtítulo
            for l in sub_lines:
                bbox = draw_temp.textbbox((0, 0), l, font=sub_font)
                lh = bbox[3] - bbox[1]
                line_heights.append((l, sub_font, lh, cfg.subtitle_color, False))
                total_text_h += lh + line_spacing

        start_y = cy - (total_text_h // 2)

        # Se solicitado cartão decorativo (card/badge)
        if cfg.box_card:
            card_w = 980
            card_h = total_text_h + 120
            card_x = cx - (card_w // 2)
            card_y = start_y - 60

            # Card background
            card_img = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
            cdraw = ImageDraw.Draw(card_img)

            # Cor suave com alfa
            bg_card_rgb = hex_to_rgb(cfg.box_card_color)
            cdraw.rounded_rectangle(
                [(0, 0), (card_w, card_h)],
                radius=32,
                fill=bg_card_rgb + (235,),
                outline=(226, 232, 240, 255),
                width=4
            )

            # Sombra suave sob o cartão
            pad = 40
            c_shadow = Image.new("RGBA", (card_w + pad * 2, card_h + pad * 2), (0, 0, 0, 0))
            cs_draw = ImageDraw.Draw(c_shadow)
            cs_draw.rounded_rectangle(
                [(pad, pad), (pad + card_w, pad + card_h)],
                radius=32,
                fill=(15, 23, 42, 60)
            )
            c_shadow = c_shadow.filter(ImageFilter.GaussianBlur(radius=25))

            canvas_rgba = canvas.convert("RGBA")
            canvas_rgba.alpha_composite(c_shadow, (card_x - pad + 8, card_y - pad + 12))
            canvas_rgba.alpha_composite(card_img, (card_x, card_y))
            canvas.paste(canvas_rgba.convert("RGB"), (0, 0))

        # Renderiza o texto linha por linha
        curr_y = start_y
        for text_str, font, lh, color_hex, is_title in line_heights:
            color_rgb = hex_to_rgb(color_hex)
            cls._draw_text_line_with_symbols(
                canvas=canvas,
                text=text_str,
                font=font,
                center_x=cx,
                y=curr_y,
                color_rgb=color_rgb,
                shadow=cfg.shadow
            )
            curr_y += lh + (54 if is_title and text_str == title_lines[-1] and sub_lines else line_spacing)

    @classmethod
    def _draw_text_line_with_symbols(
        cls,
        canvas: Image.Image,
        text: str,
        font: ImageFont.FreeTypeFont,
        center_x: int,
        y: int,
        color_rgb: Tuple[int, int, int],
        shadow: bool
    ) -> None:
        """Desenha uma linha de texto com suporte a sombras e corações decorativos perfeitos."""
        draw = ImageDraw.Draw(canvas)

        # Detecta se a linha contém coração ❤️ ou ❤
        has_heart = "❤️" in text or "❤" in text

        if not has_heart:
            bbox = draw.textbbox((0, 0), text, font=font)
            line_w = bbox[2] - bbox[0]
            draw_x = center_x - (line_w // 2)

            if shadow:
                draw.text((draw_x + 3, y + 4), text, font=font, fill=(15, 23, 42, 90))
            draw.text((draw_x, y), text, font=font, fill=color_rgb)
        else:
            # Renderiza parte textual + coração vermelho vibrante vetorizado
            clean_text = text.replace("❤️", "").replace("❤", "").strip()
            bbox = draw.textbbox((0, 0), clean_text, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]

            heart_size = max(38, int(text_h * 1.05))
            gap = 20
            total_w = text_w + gap + heart_size
            start_x = center_x - (total_w // 2)

            if shadow:
                draw.text((start_x + 3, y + 4), clean_text, font=font, fill=(15, 23, 42, 90))
            draw.text((start_x, y), clean_text, font=font, fill=color_rgb)

            # Desenha o coração vetorizado
            hx = start_x + text_w + gap
            hy = y + (text_h - heart_size) // 2 + 4
            cls._draw_vector_heart(canvas, hx, hy, heart_size)

    @classmethod
    def _draw_vector_heart(cls, canvas: Image.Image, x: int, y: int, size: int) -> None:
        """Desenha um coração perfeito, brilhante e anti-aliased na resolução gráfica informada."""
        ss = 4
        big_size = size * ss
        heart_layer = Image.new("RGBA", (big_size, big_size), (0, 0, 0, 0))
        hdraw = ImageDraw.Draw(heart_layer)

        # Curva de coração paramétrica suave preenchida
        points = []
        center_bx = big_size // 2
        center_by = int(big_size * 0.45)
        scale = big_size * 0.026

        for deg in range(0, 360, 2):
            t = math.radians(deg)
            # Equação clássica de cardioide/coração
            hx = 16 * (math.sin(t) ** 3)
            hy = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
            px = center_bx + (hx * scale)
            py = center_by + (hy * scale)
            points.append((px, py))

        # Vermelho carmim vivo com sutil degradê
        hdraw.polygon(points, fill=(225, 29, 72, 255))

        # Reduz com Lanczos para anti-aliasing de nível editorial
        heart_final = heart_layer.resize((size, size), Image.Resampling.LANCZOS)

        canvas_rgba = canvas.convert("RGBA")
        canvas_rgba.alpha_composite(heart_final, (x, y))
        canvas.paste(canvas_rgba.convert("RGB"), (0, 0))

    @classmethod
    def _wrap_text(cls, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
        """Quebra linhas inteligentemente para não ultrapassar a largura do bloco de texto."""
        if not text:
            return []

        # Respeita quebras manuais de linha
        paragraphs = text.split("\n")
        lines = []

        dummy_img = Image.new("RGB", (10, 10))
        draw = ImageDraw.Draw(dummy_img)

        for p in paragraphs:
            words = p.split()
            if not words:
                continue

            current_line = words[0]
            for w in words[1:]:
                candidate = f"{current_line} {w}"
                bbox = draw.textbbox((0, 0), candidate, font=font)
                if (bbox[2] - bbox[0]) <= max_width:
                    current_line = candidate
                else:
                    lines.append(current_line)
                    current_line = w
            lines.append(current_line)

        return lines

    @classmethod
    def _create_proof_sheet(cls, final_art: Image.Image) -> Image.Image:
        """
        Gera uma prova técnica com marcações de área de impressão:
        - Margens de sangria de 5mm (cerca de 59px a 300 DPI)
        - Centro da caneca
        - Áreas dos lados esquerdo e direito (visíveis ao segurar a alça)
        """
        w, h = final_art.size
        proof = final_art.copy()
        draw = ImageDraw.Draw(proof)

        margin_px = round((5.0 * cls.DPI) / 25.4)  # ~59 px
        guide_color = (37, 99, 235, 180)  # Azul suave
        handle_color = (239, 68, 68, 160) # Vermelho suave

        # 1. Margem de segurança de 5mm pontilhada
        for x in range(margin_px, w - margin_px, 16):
            draw.line([(x, margin_px), (min(x + 8, w - margin_px), margin_px)], fill=guide_color, width=2)
            draw.line([(x, h - margin_px), (min(x + 8, w - margin_px), h - margin_px)], fill=guide_color, width=2)

        for y in range(margin_px, h - margin_px, 16):
            draw.line([(margin_px, y), (margin_px, min(y + 8, h - margin_px))], fill=guide_color, width=2)
            draw.line([(w - margin_px, y), (w - margin_px, min(y + 8, h - margin_px))], fill=guide_color, width=2)

        # 2. Linha do Centro
        center_x = w // 2
        for y in range(0, h, 20):
            draw.line([(center_x, y), (center_x, min(y + 10, h))], fill=(100, 116, 139, 200), width=2)

        # 3. Zonas próximas da alça (extremidades 0-140px e (w-140)-w)
        draw.rectangle([(0, 0), (140, 40)], fill=(255, 255, 255, 200))
        draw.text((10, 10), "ZONA DA ALÇA", fill=handle_color)

        draw.rectangle([(w - 140, 0), (w, 40)], fill=(255, 255, 255, 200))
        draw.text((w - 130, 10), "ZONA DA ALÇA", fill=handle_color)

        return proof

    @classmethod
    def _resolve_path(cls, path_str: str, base_dir: Optional[Path]) -> Optional[Path]:
        """Resolve o caminho de arquivo relativo ou absoluto."""
        p = Path(path_str)
        if p.is_absolute() and p.exists():
            return p
        if base_dir:
            cand = base_dir / path_str
            if cand.exists():
                return cand
        if p.exists():
            return p
        return None
