"""Gerador de 5 modelos de artes de caneca (22x9.5cm @ 300 DPI) preservando 100% as fotos originais."""

from pathlib import Path
from typing import Tuple, List, Optional
import math
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from src.utils import mm_to_pixels


# Dimensões exatas a 300 DPI
W_PX = 2598  # 220 mm
H_PX = 1122  # 95 mm
DPI = 300


def get_font(name: str, size: int) -> ImageFont.FreeTypeFont:
    """Carrega fonte TrueType do Windows com fallbacks seguros."""
    win_fonts = Path("C:/Windows/Fonts")
    mapping = {
        "georgia": "georgia.ttf",
        "georgia_bold": "georgiab.ttf",
        "georgia_italic": "georgiai.ttf",
        "segoe": "segoeui.ttf",
        "segoe_bold": "segoeuib.ttf",
        "segoe_italic": "segoeuii.ttf",
        "segoe_print": "segoepr.ttf",
        "segoe_print_bold": "segoeprb.ttf",
        "segoe_script": "segoesc.ttf",
        "arial": "arial.ttf",
        "arial_bold": "arialbd.ttf",
    }
    font_file = mapping.get(name.lower(), f"{name}.ttf")
    fp = win_fonts / font_file
    if fp.exists():
        try:
            return ImageFont.truetype(str(fp), size)
        except Exception:
            pass
    for fb in ["segoeuib.ttf", "arialbd.ttf", "georgia.ttf", "arial.ttf"]:
        fbp = win_fonts / fb
        if fbp.exists():
            try:
                return ImageFont.truetype(str(fbp), size)
            except Exception:
                pass
    return ImageFont.load_default()


def crop_cover(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Recorta a imagem proporcionalmente preenchendo toda a área alvo (Aspect Fill)."""
    rgba = img.convert("RGBA")
    scale = max(target_w / rgba.width, target_h / rgba.height)
    sw, sh = round(rgba.width * scale), round(rgba.height * scale)
    resized = rgba.resize((sw, sh), Image.Resampling.LANCZOS)
    cx = (sw - target_w) // 2
    cy = (sh - target_h) // 2
    return resized.crop((cx, cy, cx + target_w, cy + target_h))


def create_vector_heart(size: int, color_rgb: Tuple[int, int, int]) -> Image.Image:
    """Gera um coração vetorizado suave e perfeito em qualquer resolução."""
    ss = 4
    big_size = size * ss
    layer = Image.new("RGBA", (big_size, big_size), (0, 0, 0, 0))
    ldraw = ImageDraw.Draw(layer)
    points = []
    cbx = big_size // 2
    cby = int(big_size * 0.45)
    scale = big_size * 0.026
    for deg in range(0, 360, 2):
        t = math.radians(deg)
        hx = 16 * (math.sin(t) ** 3)
        hy = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
        points.append((cbx + hx * scale, cby + hy * scale))
    ldraw.polygon(points, fill=color_rgb + (255,))
    return layer.resize((size, size), Image.Resampling.LANCZOS)


def draw_soft_shadow(w: int, h: int, radius: int = 16, blur: int = 30, opacity: float = 0.25) -> Tuple[Image.Image, int]:
    """Cria uma imagem RGBA com sombra suave arredondada."""
    pad = blur * 2
    s_img = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(s_img)
    alpha = int(255 * opacity)
    sdraw.rounded_rectangle([(pad, pad), (pad + w, pad + h)], radius=radius, fill=(15, 23, 42, alpha))
    blurred = s_img.filter(ImageFilter.GaussianBlur(radius=blur))
    return blurred, pad


# ==============================================================================
# ESTILO 1: GALERIA MINIMALISTA / EDITORIAL CHIC
# ==============================================================================
def generate_style_1_editorial(img_casal: Image.Image, img_familia: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (W_PX, H_PX), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)

    pw, ph = 760, 940
    py = (H_PX - ph) // 2
    x_casal = 220
    x_familia = W_PX - 220 - pw

    # Molduras de Galeria (com paspatur branco fino e contorno grafite)
    border_color = (30, 41, 59)

    for x_pos, src_img in [(x_casal, img_casal), (x_familia, img_familia)]:
        # Sombra
        shadow, pad = draw_soft_shadow(pw, ph, radius=6, blur=32, opacity=0.18)
        canvas_rgba = canvas.convert("RGBA")
        canvas_rgba.alpha_composite(shadow, (x_pos - pad + 6, py - pad + 10))
        canvas.paste(canvas_rgba.convert("RGB"), (0, 0))

        # Foto cortada
        cropped = crop_cover(src_img, pw, ph)
        canvas.paste(cropped, (x_pos, py))

        # Moldura fina de galeria
        draw.rectangle([(x_pos, py), (x_pos + pw, py + ph)], outline=border_color, width=4)

    # Bloco Central Tipográfico Editorial
    cx = W_PX // 2
    cy = H_PX // 2

    # Título "FAMÍLIA" espaçado
    f_title = get_font("georgia_bold", 54)
    title_text = "F A M Í L I A"
    bbox_t = draw.textbbox((0, 0), title_text, font=f_title)
    draw.text((cx - (bbox_t[2] - bbox_t[0]) // 2, cy - 130), title_text, font=f_title, fill=(15, 23, 42))

    # Linha Dourada Refinada
    gold = (197, 160, 89)
    draw.line([(cx - 90, cy - 45), (cx + 90, cy - 45)], fill=gold, width=3)
    # Losango no meio da linha
    draw.polygon([(cx, cy - 51), (cx + 6, cy - 45), (cx, cy - 39), (cx - 6, cy - 45)], fill=gold)

    # Frase Poética
    f_italic = get_font("georgia_italic", 36)
    l1 = "Onde a nossa história começa"
    l2 = "e o amor nunca termina."
    bbox_l1 = draw.textbbox((0, 0), l1, font=f_italic)
    bbox_l2 = draw.textbbox((0, 0), l2, font=f_italic)
    draw.text((cx - (bbox_l1[2] - bbox_l1[0]) // 2, cy - 10), l1, font=f_italic, fill=(71, 85, 105))
    draw.text((cx - (bbox_l2[2] - bbox_l2[0]) // 2, cy + 45), l2, font=f_italic, fill=(71, 85, 105))

    # Ano sutil
    f_year = get_font("georgia", 28)
    draw.text((cx - 45, cy + 125), "• 2026 •", font=f_year, fill=(148, 163, 184))

    return canvas


# ==============================================================================
# ESTILO 2: MOLDURAS EM ARCO & FORMAS ORGÂNICAS (BOHO CHIC)
# ==============================================================================
def create_arch_mask(w: int, h: int, ss: int = 2) -> Image.Image:
    """Cria máscara com topo em semicírculo (Arco Romano) com supersampling anti-aliasing."""
    bw, bh = w * ss, h * ss
    mask = Image.new("L", (bw, bh), 0)
    mdraw = ImageDraw.Draw(mask)
    r = bw // 2
    # Semicírculo superior
    mdraw.pieslice([(0, 0), (bw, bw)], 180, 360, fill=255)
    # Retângulo inferior
    mdraw.rectangle([(0, r), (bw, bh)], fill=255)
    return mask.resize((w, h), Image.Resampling.LANCZOS)


def generate_style_2_boho_arch(img_casal: Image.Image, img_familia: Image.Image) -> Image.Image:
    # Fundo linho / areia bem clarinho
    bg_color = (250, 248, 244)
    canvas = Image.new("RGB", (W_PX, H_PX), bg_color)

    pw, ph = 760, 960
    py = (H_PX - ph) // 2 + 10
    x_casal = 220
    x_familia = W_PX - 220 - pw

    arch_mask = create_arch_mask(pw, ph)
    gold = (197, 160, 89)

    for x_pos, src_img in [(x_casal, img_casal), (x_familia, img_familia)]:
        # Sombra do arco
        pad = 60
        s_img = Image.new("RGBA", (pw + pad * 2, ph + pad * 2), (0, 0, 0, 0))
        sdraw = ImageDraw.Draw(s_img)
        # desenha o arco na sombra
        s_mask = create_arch_mask(pw, ph, ss=1)
        s_fill = Image.new("RGBA", (pw, ph), (40, 30, 20, 45))
        s_img.paste(s_fill, (pad, pad), mask=s_mask)
        blurred_s = s_img.filter(ImageFilter.GaussianBlur(radius=28))

        canvas_rgba = canvas.convert("RGBA")
        canvas_rgba.alpha_composite(blurred_s, (x_pos - pad + 8, py - pad + 12))

        # Foto no arco
        cropped = crop_cover(src_img, pw, ph)
        arc_photo = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
        arc_photo.paste(cropped, (0, 0), mask=arch_mask)

        # Borda dourada em arco
        ss = 2
        b_large = Image.new("RGBA", (pw * ss, ph * ss), (0, 0, 0, 0))
        bdraw = ImageDraw.Draw(b_large)
        bw, bh = pw * ss, ph * ss
        br = bw // 2
        b_color = gold + (255,)
        bdraw.arc([(0, 0), (bw, bw)], 180, 360, fill=b_color, width=6)
        bdraw.line([(0, br), (0, bh)], fill=b_color, width=6)
        bdraw.line([(bw - 1, br), (bw - 1, bh)], fill=b_color, width=6)
        bdraw.line([(0, bh - 1), (bw - 1, bh - 1)], fill=b_color, width=6)
        b_small = b_large.resize((pw, ph), Image.Resampling.LANCZOS)

        arc_final = Image.alpha_composite(arc_photo, b_small)
        canvas_rgba.alpha_composite(arc_final, (x_pos, py))
        canvas.paste(canvas_rgba.convert("RGB"), (0, 0))

    # Centro: Tipografia e ramos orgânicos
    draw = ImageDraw.Draw(canvas)
    cx = W_PX // 2
    cy = H_PX // 2

    # Ramo botânico minimalista superior
    draw.arc([(cx - 70, cy - 170), (cx + 70, cy - 90)], 190, 350, fill=gold, width=3)
    # Folhinhas simples
    for leaf_angle in [-40, -10, 20]:
        lx = cx + int(50 * math.sin(math.radians(leaf_angle)))
        ly = cy - 130 + int(35 * math.cos(math.radians(leaf_angle)))
        draw.ellipse([(lx - 6, ly - 3), (lx + 6, ly + 3)], fill=gold)

    f_script = get_font("segoe_script", 54)
    f_sub = get_font("georgia", 30)

    t_text = "O amor que nos une"
    bbox_t = draw.textbbox((0, 0), t_text, font=f_script)
    draw.text((cx - (bbox_t[2] - bbox_t[0]) // 2, cy - 40), t_text, font=f_script, fill=(90, 70, 45))

    sub_text = "Nossa Família • Nosso Lar"
    bbox_s = draw.textbbox((0, 0), sub_text, font=f_sub)
    draw.text((cx - (bbox_s[2] - bbox_s[0]) // 2, cy + 50), sub_text, font=f_sub, fill=(156, 130, 98))

    return canvas


# ==============================================================================
# ESTILO 3: SCRAPBOOK AFETIVO / FITA WASHI TAPE
# ==============================================================================
def draw_washi_tape(w: int, h: int, color_rgba: Tuple[int, int, int, int]) -> Image.Image:
    """Cria uma fita washi tape translúcida com cortes de fita adesiva."""
    tape = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    tdraw = ImageDraw.Draw(tape)
    # Retângulo de fita
    tdraw.rectangle([(0, 0), (w, h)], fill=color_rgba)
    # Padrão de textura sutil de fita adesiva
    for x in range(0, w, 8):
        tdraw.line([(x, 0), (x, h)], fill=(255, 255, 255, 35), width=2)
    return tape


def generate_style_3_scrapbook(img_casal: Image.Image, img_familia: Image.Image) -> Image.Image:
    # Fundo branco linho sutil
    canvas = Image.new("RGB", (W_PX, H_PX), (252, 252, 250))

    # Dimensões de cada impressão fotográfica
    pw, ph = 760, 930
    border = 26

    # Cores de fita Washi Tape
    tape_gold = (234, 179, 8, 205)   # Amarelo mostarda
    tape_rose = (225, 29, 72, 195)   # Rosa / Carmim suave

    # Processa Foto 1 (Casal, inclinada a -3.2°)
    photo_casal = crop_cover(img_casal, pw - border * 2, ph - border * 2)
    card_1 = Image.new("RGBA", (pw, ph), (255, 255, 255, 255))
    card_1.paste(photo_casal, (border, border))
    c1_draw = ImageDraw.Draw(card_1)
    c1_draw.rectangle([(0, 0), (pw, ph)], outline=(226, 232, 240, 255), width=2)

    # Legenda escrita à mão
    f_hand = get_font("segoe_print_bold", 38)
    t1 = "Nós dois ❤️"
    bbox_t1 = c1_draw.textbbox((0, 0), t1, font=f_hand)
    # faixa branca inferior mais larga para legenda
    # Rotaciona Foto 1
    rot_1 = card_1.rotate(3.2, resample=Image.Resampling.BICUBIC, expand=True)

    # Foto 2 (Família, inclinada a +3.2°)
    photo_fam = crop_cover(img_familia, pw - border * 2, ph - border * 2)
    card_2 = Image.new("RGBA", (pw, ph), (255, 255, 255, 255))
    card_2.paste(photo_fam, (border, border))
    c2_draw = ImageDraw.Draw(card_2)
    c2_draw.rectangle([(0, 0), (pw, ph)], outline=(226, 232, 240, 255), width=2)
    rot_2 = card_2.rotate(-3.2, resample=Image.Resampling.BICUBIC, expand=True)

    # Sombra de cada foto
    for rot_card, cx_target in [(rot_1, 560), (rot_2, 2038)]:
        rw, rh = rot_card.size
        pad = 60
        s_img = Image.new("RGBA", (rw + pad * 2, rh + pad * 2), (0, 0, 0, 0))
        s_mask = rot_card.split()[3]
        s_fill = Image.new("RGBA", (rw, rh), (15, 23, 42, 55))
        s_img.paste(s_fill, (pad, pad), mask=s_mask)
        blurred_s = s_img.filter(ImageFilter.GaussianBlur(radius=26))

        canvas_rgba = canvas.convert("RGBA")
        canvas_rgba.alpha_composite(blurred_s, (cx_target - rw // 2 - pad + 8, (H_PX - rh) // 2 - pad + 12))
        canvas_rgba.alpha_composite(rot_card, (cx_target - rw // 2, (H_PX - rh) // 2))
        canvas.paste(canvas_rgba.convert("RGB"), (0, 0))

    # Aplica Washi Tapes nos cantos
    canvas_rgba = canvas.convert("RGBA")
    # Fita 1: topo esquerdo da foto 1 (amarelo)
    tape1 = draw_washi_tape(160, 48, tape_gold).rotate(18, resample=Image.Resampling.BICUBIC, expand=True)
    canvas_rgba.alpha_composite(tape1, (240, 60))
    # Fita 2: base direita da foto 1 (carmim)
    tape2 = draw_washi_tape(150, 44, tape_rose).rotate(-14, resample=Image.Resampling.BICUBIC, expand=True)
    canvas_rgba.alpha_composite(tape2, (780, 960))

    # Fita 3: topo direito da foto 2 (carmim)
    tape3 = draw_washi_tape(160, 48, tape_rose).rotate(-16, resample=Image.Resampling.BICUBIC, expand=True)
    canvas_rgba.alpha_composite(tape3, (2160, 60))
    # Fita 4: base esquerda da foto 2 (amarelo)
    tape4 = draw_washi_tape(150, 44, tape_gold).rotate(14, resample=Image.Resampling.BICUBIC, expand=True)
    canvas_rgba.alpha_composite(tape4, (1680, 960))

    canvas = canvas_rgba.convert("RGB")
    draw = ImageDraw.Draw(canvas)

    # Centro: Recadinho afetivo
    cx = W_PX // 2
    cy = H_PX // 2
    f_note = get_font("segoe_print_bold", 48)
    f_sub = get_font("segoe_print", 34)

    n1 = "Memórias Eternas"
    n2_text = "Para Sempre Nós"
    bbox_n1 = draw.textbbox((0, 0), n1, font=f_note)
    bbox_n2 = draw.textbbox((0, 0), n2_text, font=f_sub)
    draw.text((cx - (bbox_n1[2] - bbox_n1[0]) // 2, cy - 60), n1, font=f_note, fill=(30, 41, 59))

    t2_w = bbox_n2[2] - bbox_n2[0]
    heart_sz = 30
    gap = 14
    total_w2 = t2_w + gap + heart_sz
    start_x2 = cx - (total_w2 // 2)
    draw.text((start_x2, cy + 20), n2_text, font=f_sub, fill=(225, 29, 72))
    heart_img = create_vector_heart(heart_sz, (225, 29, 72))
    canvas.paste(heart_img, (start_x2 + t2_w + gap, cy + 26), mask=heart_img)

    return canvas


# ==============================================================================
# ESTILO 4: SPOTIFY MUSIC PLAYER (MODERNO & INTERATIVO)
# ==============================================================================
def draw_spotify_player_block(
    canvas: Image.Image,
    photo: Image.Image,
    center_x: int,
    center_y: int,
    music_title: str,
    artist_name: str,
    current_time: str,
    total_time: str,
    progress_ratio: float = 0.65
) -> None:
    draw = ImageDraw.Draw(canvas)

    # Card da foto (Quadrada clássica do Spotify: 620 x 620 px)
    card_size = 620
    photo_cropped = crop_cover(photo, card_size, card_size)

    # Cantos arredondados na capa
    mask_c = Image.new("L", (card_size, card_size), 0)
    ImageDraw.Draw(mask_c).rounded_rectangle([(0, 0), (card_size, card_size)], radius=18, fill=255)

    card_x = center_x - (card_size // 2)
    card_y = center_y - 340

    # Sombra da capa
    shadow, pad = draw_soft_shadow(card_size, card_size, radius=18, blur=34, opacity=0.35)
    canvas_rgba = canvas.convert("RGBA")
    canvas_rgba.alpha_composite(shadow, (card_x - pad + 8, card_y - pad + 14))
    canvas.paste(canvas_rgba.convert("RGB"), (0, 0))

    canvas.paste(photo_cropped, (card_x, card_y), mask=mask_c)

    # Título da Música e Artista
    f_title = get_font("segoe_bold", 42)
    f_artist = get_font("segoe", 30)
    draw.text((card_x, card_y + card_size + 24), music_title, font=f_title, fill=(255, 255, 255))
    draw.text((card_x, card_y + card_size + 78), artist_name, font=f_artist, fill=(179, 179, 179))

    # Coração verde de curtir do Spotify (lado direito do título)
    heart_green = (29, 185, 84)
    hx = card_x + card_size - 40
    hy = card_y + card_size + 28
    sp_heart = create_vector_heart(32, heart_green)
    canvas.paste(sp_heart, (hx, hy), mask=sp_heart)

    # Barra de Progresso
    bar_w = card_size
    bar_y = card_y + card_size + 140
    # Linha de fundo cinza
    draw.rounded_rectangle([(card_x, bar_y), (card_x + bar_w, bar_y + 8)], radius=4, fill=(83, 83, 83))
    # Linha ativa branca
    prog_w = int(bar_w * progress_ratio)
    draw.rounded_rectangle([(card_x, bar_y), (card_x + prog_w, bar_y + 8)], radius=4, fill=(255, 255, 255))
    # Bolinha do indicador de progresso
    draw.ellipse([(card_x + prog_w - 6, bar_y - 4), (card_x + prog_w + 10, bar_y + 12)], fill=(255, 255, 255))

    # Marcadores de Tempo
    f_time = get_font("segoe", 22)
    draw.text((card_x, bar_y + 18), current_time, font=f_time, fill=(179, 179, 179))
    bbox_tt = draw.textbbox((0, 0), total_time, font=f_time)
    draw.text((card_x + bar_w - (bbox_tt[2] - bbox_tt[0]), bar_y + 18), total_time, font=f_time, fill=(179, 179, 179))

    # Controles do Player (Shuffle, Previous, Play, Next, Repeat)
    ctrl_y = bar_y + 70
    mid_x = card_x + (card_size // 2)

    # Botão de Play (círculo branco grande com triângulo preto)
    play_r = 34
    draw.ellipse([(mid_x - play_r, ctrl_y - play_r), (mid_x + play_r, ctrl_y + play_r)], fill=(255, 255, 255))
    # Triângulo play
    draw.polygon([(mid_x - 10, ctrl_y - 14), (mid_x + 14, ctrl_y), (mid_x - 10, ctrl_y + 14)], fill=(18, 18, 18))

    # Previous (<<)
    draw.polygon([(mid_x - 85, ctrl_y - 12), (mid_x - 102, ctrl_y), (mid_x - 85, ctrl_y + 12)], fill=(255, 255, 255))
    draw.line([(mid_x - 104, ctrl_y - 12), (mid_x - 104, ctrl_y + 12)], fill=(255, 255, 255), width=3)

    # Next (>>)
    draw.polygon([(mid_x + 85, ctrl_y - 12), (mid_x + 102, ctrl_y), (mid_x + 85, ctrl_y + 12)], fill=(255, 255, 255))
    draw.line([(mid_x + 104, ctrl_y - 12), (mid_x + 104, ctrl_y + 12)], fill=(255, 255, 255), width=3)


def generate_style_4_spotify(img_casal: Image.Image, img_familia: Image.Image) -> Image.Image:
    # Fundo Spotify Dark Premium (#121212)
    canvas = Image.new("RGB", (W_PX, H_PX), (18, 18, 18))

    # Player 1 (Casal, Lado Esquerdo)
    draw_spotify_player_block(
        canvas=canvas,
        photo=img_casal,
        center_x=580,
        center_y=H_PX // 2,
        music_title="Apenas Você",
        artist_name="Nossa História de Amor",
        current_time="2:14",
        total_time="3:45",
        progress_ratio=0.60
    )

    # Player 2 (Família, Lado Direito)
    draw_spotify_player_block(
        canvas=canvas,
        photo=img_familia,
        center_x=2018,
        center_y=H_PX // 2,
        music_title="Lar É Onde Vocês Estão",
        artist_name="Minha Família, Minha Vida",
        current_time="1:48",
        total_time="3:20",
        progress_ratio=0.54
    )

    # Centro: Ondas Sonoras Verdes do Spotify e Título
    draw = ImageDraw.Draw(canvas)
    cx = W_PX // 2
    cy = H_PX // 2

    green = (29, 185, 84)

    # Barras de som animadas no meio
    bar_heights = [18, 38, 70, 110, 150, 95, 130, 80, 120, 160, 140, 85, 55, 24]
    start_bx = cx - (len(bar_heights) * 14) // 2
    for i, bh in enumerate(bar_heights):
        bx = start_bx + (i * 14)
        draw.rounded_rectangle([(bx, cy - 80 - bh // 2), (bx + 7, cy - 80 + bh // 2)], radius=3, fill=green)

    f_sp_title = get_font("segoe_bold", 38)
    f_sp_sub = get_font("segoe", 26)

    t1 = "Nossa Trilha Sonora"
    bbox_t1 = draw.textbbox((0, 0), t1, font=f_sp_title)
    draw.text((cx - (bbox_t1[2] - bbox_t1[0]) // 2, cy + 30), t1, font=f_sp_title, fill=(255, 255, 255))

    t2 = "Tocando os melhores momentos"
    bbox_t2 = draw.textbbox((0, 0), t2, font=f_sp_sub)
    draw.text((cx - (bbox_t2[2] - bbox_t2[0]) // 2, cy + 85), t2, font=f_sp_sub, fill=(179, 179, 179))

    return canvas


# ==============================================================================
# ESTILO 5: PELÍCULA DE FILME RETRÔ (FILM STRIP 35MM)
# ==============================================================================
def generate_style_5_film_strip(img_casal: Image.Image, img_familia: Image.Image) -> Image.Image:
    # Fundo branco puro
    canvas = Image.new("RGB", (W_PX, H_PX), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)

    # Faixa da Película atravessando horizontalmente de 60px a W_PX-60px
    strip_h = 980
    strip_y = (H_PX - strip_h) // 2
    strip_x = 70
    strip_w = W_PX - 140

    film_black = (24, 24, 27)
    # Sombra da película
    shadow, pad = draw_soft_shadow(strip_w, strip_h, radius=12, blur=36, opacity=0.20)
    canvas_rgba = canvas.convert("RGBA")
    canvas_rgba.alpha_composite(shadow, (strip_x - pad + 6, strip_y - pad + 12))
    canvas.paste(canvas_rgba.convert("RGB"), (0, 0))

    # Fita de filme preta
    draw.rounded_rectangle([(strip_x, strip_y), (strip_x + strip_w, strip_y + strip_h)], radius=12, fill=film_black)

    # Perfurações de Filme 35mm (Sprocket holes brancos no topo e na base)
    sprocket_w = 28
    sprocket_h = 42
    sprocket_gap = 48
    num_sprockets = strip_w // sprocket_gap

    sprocket_color = (255, 255, 255)
    for i in range(num_sprockets):
        sx = strip_x + 30 + (i * sprocket_gap)
        if (sx + sprocket_w) < (strip_x + strip_w - 20):
            # Topo
            draw.rounded_rectangle([(sx, strip_y + 18), (sx + sprocket_w, strip_y + 18 + sprocket_h)], radius=6, fill=sprocket_color)
            # Base
            draw.rounded_rectangle([(sx, strip_y + strip_h - 18 - sprocket_h), (sx + sprocket_w, strip_y + strip_h - 18)], radius=6, fill=sprocket_color)

    # Janelas das Fotos
    pw = 880
    ph = 760
    py = strip_y + 95

    x_frame1 = strip_x + 180
    x_frame2 = strip_x + strip_w - 180 - pw

    # Fotos cortadas dentro dos frames
    cropped1 = crop_cover(img_casal, pw, ph)
    canvas.paste(cropped1, (x_frame1, py))

    cropped2 = crop_cover(img_familia, pw, ph)
    canvas.paste(cropped2, (x_frame2, py))

    # Bordas e textos de filme
    amber = (245, 158, 11)  # Laranja negativo clássico
    f_film = get_font("segoe_bold", 24)

    # Frame 1 Texts
    draw.text((x_frame1, py - 32), "KODAK PORTRA 400 • 12A", font=f_film, fill=amber)
    draw.text((x_frame1, py + ph + 8), "▲ 12   O INÍCIO • NÓS DOIS", font=f_film, fill=amber)

    # Frame 2 Texts
    draw.text((x_frame2, py - 32), "KODAK PORTRA 400 • 13A", font=f_film, fill=amber)
    draw.text((x_frame2, py + ph + 8), "▲ 13   NOSSO PRESENTE • FAMÍLIA", font=f_film, fill=amber)

    # Centro: Divisória e Claquete
    cx = W_PX // 2
    cy = H_PX // 2

    # Linha divisória de filme
    draw.line([(cx, py + 20), (cx, py + ph - 20)], fill=(63, 63, 70), width=3)

    f_cen_title = get_font("georgia_bold", 36)
    f_cen_sub = get_font("georgia_italic", 26)
    draw.text((cx - 80, cy - 40), "CENA 01", font=f_cen_title, fill=(255, 255, 255))
    draw.text((cx - 105, cy + 15), "História Real", font=f_cen_sub, fill=(161, 161, 170))

    return canvas
