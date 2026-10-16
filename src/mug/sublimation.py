"""Motor de tratamento de cor e compensação técnica para Sublimação em Canecas de Cerâmica (MUG).

Controla ganho de ponto térmico, empastamento de sombras (shadow crushing), queima de resina
e saturação de cor em prensas térmicas de cerâmica (~200°C / 180s).
Gera simultaneamente:
1. Versão Impressão Sublimática: Cores tratadas termicamente para a impressora a 300 DPI.
2. Versão Prévia do Cliente: Visualização digital fiel para tela e aprovação via WhatsApp.
3. Versão Mockup 3D: Simulação da caneca de cerâmica curva com luz, reflexo e sombra.
"""

from pathlib import Path
from typing import Dict, Optional, Tuple, Union
import math
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps


class SublimationEngine:
    """Motor de compensação cromática para sublimação e gerador de apresentações comerciais."""

    # Padrão da fita/manta de caneca
    CANVAS_WIDTH_MM = 220.0
    CANVAS_HEIGHT_MM = 95.0
    TARGET_WIDTH_PX = 2598
    TARGET_HEIGHT_PX = 1122
    DPI = 300

    @classmethod
    def create_sublimation_lut(
        cls,
        gamma: float = 1.0,
        black_pedestal: int = 0,
        white_threshold: int = 252,
        gain: float = 1.0
    ) -> list:
        """
        Cria uma Lookup Table (LUT) de 256 valores para mapeamento de tons.
        - Preserva o preto puro (0 -> black_pedestal=0) para que o perfil ICC no Corel aplique densidade total.
        - Curva gama neutra (1.0) ou suave para evitar clareamento e perda de saturação em meios-tons.
        - Aplica ganho tonal seletivo (gain) para equilíbrio térmico e correção de dominância azulada.
        - Preserva brancos puros (>= white_threshold) intactos para manter a cerâmica branca limpa.
        """
        lut = []
        for i in range(256):
            if i >= white_threshold:
                # Brancos e quase-brancos viram branco puro (fundo da cerâmica não gasta tinta)
                lut.append(255)
                continue

            x = i / 255.0
            # Aplica correção gama
            x_gamma = math.pow(x, 1.0 / max(0.01, gamma))

            # Aplica ganho de canal seletivo
            x_mod = x_gamma * gain

            # Mapeia dentro da faixa [black_pedestal, 255]
            val = round(black_pedestal + (255.0 - black_pedestal) * x_mod)
            val = max(0, min(255, val))
            lut.append(val)
        return lut

    @classmethod
    def prepare_for_sublimation(
        cls,
        image: Image.Image,
        gamma: float = 1.0,
        black_pedestal: int = 0,
        saturation_factor: float = 1.08,
        contrast_factor: float = 1.05,
        red_gain: float = 1.03,
        blue_gain: float = 0.96,
        sharpen: bool = True
    ) -> Image.Image:
        """
        Aplica o tratamento cromático prévio para impressão sublimática integrada ao Perfil ICC (CorelDRAW).

        Efeitos aplicados:
        1. Preservação do preto 100% (black_pedestal = 0): permite que o perfil ICC deposite pretos profundos.
        2. Curva gama equilibrada (gamma = 1.0): evita o efeito lavado e esbranquiçado nos rostos.
        3. Equilíbrio de temperatura cromática: ganho suave no canal R (1.03) e redução em B (0.96)
           para neutralizar o tom frio/azulado e aquecer os tons de pele, preservando fundos brancos.
        4. Reforço de saturação (+8%) e micro-contraste (+5%): combate a opacidade na prensa.
        5. Unsharp Mask a 300 DPI: restaura a nitidez de micro-detalhes amenizados pela difusão gasosa.
        """
        rgb_img = image.convert("RGB")

        # 1. Aplica LUT tonal com balanço térmico para cada canal (R, G, B)
        lut_r = cls.create_sublimation_lut(gamma=gamma, black_pedestal=black_pedestal, gain=red_gain)
        lut_g = cls.create_sublimation_lut(gamma=gamma, black_pedestal=black_pedestal, gain=1.0)
        lut_b = cls.create_sublimation_lut(gamma=gamma, black_pedestal=black_pedestal, gain=blue_gain)

        tone_adjusted = rgb_img.point(lut_r + lut_g + lut_b)

        # 2. Modulação de saturação (devolve vivacidade sem excessos)
        color_enhancer = ImageEnhance.Color(tone_adjusted)
        sat_adjusted = color_enhancer.enhance(saturation_factor)

        # 3. Equilíbrio de micro-contraste (elimina o efeito cinza/opaco)
        contrast_enhancer = ImageEnhance.Contrast(sat_adjusted)
        contrast_adjusted = contrast_enhancer.enhance(contrast_factor)

        # 4. Nitidez de compensação de ganho de ponto (Unsharp Masking a 300 DPI)
        if sharpen:
            final_img = contrast_adjusted.filter(
                ImageFilter.UnsharpMask(radius=1.8, percent=125, threshold=3)
            )
        else:
            final_img = contrast_adjusted

        return final_img

    @classmethod
    def generate_client_preview(
        cls,
        image: Image.Image,
        include_header: bool = True
    ) -> Image.Image:
        """
        Gera a versão prévia para envio ao cliente (aprovação no WhatsApp/celular).
        Mantém a saturação e iluminação calibradas para exibição em telas digitais sRGB.
        """
        rgb_img = image.convert("RGB")

        if not include_header:
            return rgb_img

        # Cria uma prancha de apresentação de luxo para aprovação do cliente
        w, h = rgb_img.size
        pad_top = 160
        pad_bottom = 120
        pad_side = 60

        total_w = w + pad_side * 2
        total_h = h + pad_top + pad_bottom

        sheet = Image.new("RGB", (total_w, total_h), (248, 250, 252)) # Slate 50
        draw = ImageDraw.Draw(sheet)

        # Barra decorativa de cabeçalho
        draw.rectangle([(0, 0), (total_w, 8)], fill=(37, 99, 235)) # Indigo 600

        # Textos de apresentação
        title_font = cls._get_font("segoe_bold", 46)
        sub_font = cls._get_font("segoe", 26)
        meta_font = cls._get_font("segoe", 22)

        draw.text((pad_side, 45), "PRÉVIA DIGITAL PARA APROVAÇÃO", font=title_font, fill=(15, 23, 42))
        draw.text(
            (pad_side, 105),
            "Caneca de Cerâmica Personalizada • Resolução Gráfica 300 DPI (22,0 × 9,5 cm)",
            font=sub_font,
            fill=(100, 116, 139)
        )

        # Borda sutil e sombra em torno da arte
        art_x = pad_side
        art_y = pad_top

        # Moldura da arte
        draw.rectangle(
            [(art_x - 4, art_y - 4), (art_x + w + 3, art_y + h + 3)],
            outline=(226, 232, 240),
            width=3
        )
        sheet.paste(rgb_img, (art_x, art_y))

        # Rodapé
        footer_y = art_y + h + 40
        draw.text(
            (pad_side, footer_y),
            "✓ Cores calibradas para exibição em tela. A produção final sublimática é transferida em cerâmica sob alta temperatura.",
            font=meta_font,
            fill=(71, 85, 105)
        )
        draw.text(
            (total_w - pad_side - 320, footer_y),
            "STUDIO KUSTOM • ARTES EXCLUSIVAS",
            font=meta_font,
            fill=(148, 163, 184)
        )

        return sheet

    @classmethod
    def generate_mug_3d_mockup(
        cls,
        image: Image.Image,
        side: str = "both"  # "left", "right", "both", "center"
    ) -> Image.Image:
        """
        Gera um mockup 3D fotorealista simulando a caneca de cerâmica curva.
        Aplica projeção cilíndrica com mapeamento senoidal horizontal x' = sin(theta),
        gradiente de iluminação volumétrica, reflexo especular de esmalte e sombra na base.
        """
        rgb_art = image.convert("RGBA")
        art_w, art_h = rgb_art.size

        # Dimensões da caneca renderizada
        mug_w = 900
        mug_h = 1150

        if side in ("both", "triple"):
            # Renderiza três canecas: Esquerda (25%), Centro/Frente (50%) e Direita (75%)
            canvas_w = 3000
            canvas_h = 1500
            canvas = Image.new("RGBA", (canvas_w, canvas_h), (248, 250, 252, 255))

            crop_left = cls._render_single_mug_mockup(rgb_art, center_ratio=0.25, mug_w=mug_w, mug_h=mug_h, handle_left=True)
            crop_center = cls._render_single_mug_mockup(rgb_art, center_ratio=0.50, mug_w=mug_w, mug_h=mug_h, handle_left=False)
            crop_right = cls._render_single_mug_mockup(rgb_art, center_ratio=0.75, mug_w=mug_w, mug_h=mug_h, handle_left=False)

            # Cola as três canecas
            canvas.alpha_composite(crop_left, (80, 160))
            canvas.alpha_composite(crop_center, (1000, 160))
            canvas.alpha_composite(crop_right, (1920, 160))

            # Legendas elegantes
            draw = ImageDraw.Draw(canvas)
            title_font = cls._get_font("segoe_bold", 48)
            lbl_font = cls._get_font("segoe_bold", 30)
            sub_font = cls._get_font("segoe", 22)

            draw.text((canvas_w // 2, 80), "SIMULAÇÃO REALISTA DA CANECA DE CERÂMICA (300 DPI)", font=title_font, fill=(15, 23, 42), anchor="mm")

            draw.text((80 + mug_w // 2, 1380), "LADO ESQUERDO", font=lbl_font, fill=(51, 65, 85), anchor="mm")
            draw.text((80 + mug_w // 2, 1420), "(Visão Segurando com a Mão Direita)", font=sub_font, fill=(148, 163, 184), anchor="mm")

            draw.text((1000 + mug_w // 2, 1380), "CENTRO / FRENTE", font=lbl_font, fill=(225, 29, 72), anchor="mm")
            draw.text((1000 + mug_w // 2, 1420), "(Arte Principal em Destaque)", font=sub_font, fill=(100, 116, 139), anchor="mm")

            draw.text((1920 + mug_w // 2, 1380), "LADO DIREITO", font=lbl_font, fill=(51, 65, 85), anchor="mm")
            draw.text((1920 + mug_w // 2, 1420), "(Visão Segurando com a Mão Esquerda)", font=sub_font, fill=(148, 163, 184), anchor="mm")

            return canvas.convert("RGB")
        else:
            center_ratio = 0.5 if side == "center" else (0.25 if side == "left" else 0.75)
            single = cls._render_single_mug_mockup(rgb_art, center_ratio=center_ratio, mug_w=mug_w, mug_h=mug_h)
            return single.convert("RGB")

    @classmethod
    def _render_single_mug_mockup(
        cls,
        art: Image.Image,
        center_ratio: float,
        mug_w: int,
        mug_h: int,
        handle_left: bool = False
    ) -> Image.Image:
        """Renderiza uma única caneca de cerâmica com projeção cilíndrica da arte."""
        pad = 80
        total_w = mug_w + pad * 2
        total_h = mug_h + pad * 2
        mug_img = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))

        body_x = pad + (100 if handle_left else 0)
        body_y = pad + 40
        body_w = mug_w - 100
        body_h = mug_h - 120

        # 1. Sombra projetada na base da caneca
        shadow_w = int(body_w * 1.08)
        shadow_h = 70
        shadow_x = body_x + (body_w - shadow_w) // 2
        shadow_y = body_y + body_h - 25

        shadow_layer = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))
        sdraw = ImageDraw.Draw(shadow_layer)
        sdraw.ellipse(
            [(shadow_x, shadow_y), (shadow_x + shadow_w, shadow_y + shadow_h)],
            fill=(15, 23, 42, 90)
        )
        shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=25))
        mug_img.alpha_composite(shadow_layer)

        # 2. Renderiza a Alça da Caneca (Handle)
        handle_layer = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))
        hdraw = ImageDraw.Draw(handle_layer)

        hw = 150
        hh = int(body_h * 0.65)
        hy = body_y + int(body_h * 0.18)

        if handle_left:
            hx = body_x - hw + 40
            # Alça esquerda externa
            hdraw.rounded_rectangle([(hx, hy), (hx + hw, hy + hh)], radius=70, fill=(240, 243, 246, 255), outline=(210, 215, 220, 255), width=6)
            # Furo interno da alça
            hdraw.rounded_rectangle([(hx + 50, hy + 45), (hx + hw - 10, hy + hh - 45)], radius=45, fill=(0, 0, 0, 0))
        else:
            hx = body_x + body_w - 40
            # Alça direita externa
            hdraw.rounded_rectangle([(hx, hy), (hx + hw, hy + hh)], radius=70, fill=(240, 243, 246, 255), outline=(210, 215, 220, 255), width=6)
            # Furo interno da alça
            hdraw.rounded_rectangle([(hx + 10, hy + 45), (hx + hw - 50, hy + hh - 45)], radius=45, fill=(0, 0, 0, 0))

        mug_img.alpha_composite(handle_layer)

        # 3. Mapeamento da Arte com Deformação Cilíndrica (Cylindrical Wrap)
        # Recorta a porção da arte visível ao redor de center_ratio
        art_w, art_h = art.size
        fov_width = int(art_w * 0.50)  # ~180 graus da caneca visíveis
        cx = int(art_w * center_ratio)
        x1 = cx - fov_width // 2
        x2 = cx + fov_width // 2

        # Trata repetição cíclica caso ultrapasse as bordas
        wrapped_slice = Image.new("RGBA", (fov_width, art_h), (255, 255, 255, 255))
        if x1 < 0:
            left_part = art.crop((x1 % art_w, 0, art_w, art_h))
            right_part = art.crop((0, 0, x2, art_h))
            wrapped_slice.paste(left_part, (0, 0))
            wrapped_slice.paste(right_part, (left_part.width, 0))
        elif x2 > art_w:
            left_part = art.crop((x1, 0, art_w, art_h))
            right_part = art.crop((0, 0, x2 % art_w, art_h))
            wrapped_slice.paste(left_part, (0, 0))
            wrapped_slice.paste(right_part, (left_part.width, 0))
        else:
            wrapped_slice = art.crop((x1, 0, x2, art_h))

        # Redimensiona para o corpo da caneca com proporção vertical mantida
        art_scaled = wrapped_slice.resize((body_w, body_h), Image.Resampling.LANCZOS)

        # Aplica a curvatura horizontal (sinusoidal squeeze)
        # Cada coluna x na caneca corresponde a uma coordenada u = arcsin( (x - w/2)/(w/2) ) / (pi/2)
        cylindrical_art = Image.new("RGBA", (body_w, body_h), (255, 255, 255, 255))
        # Para performance ultra-rápida sem numpy, dividimos em fatias verticais finas
        num_slices = 100
        step_w = body_w / num_slices
        for s in range(num_slices):
            # Ângulo normalizado de -1 a +1
            norm_x1 = (s / num_slices) * 2.0 - 1.0
            norm_x2 = ((s + 1) / num_slices) * 2.0 - 1.0

            # Projeção de volta para a arte plana: u = sin(norm_x * pi / 2)
            u1 = math.sin(norm_x1 * (math.pi / 2.0))
            u2 = math.sin(norm_x2 * (math.pi / 2.0))

            src_x1 = max(0, int(((u1 + 1.0) / 2.0) * body_w))
            src_x2 = min(body_w, max(src_x1 + 1, int(((u2 + 1.0) / 2.0) * body_w)))

            dst_x1 = int(s * step_w)
            dst_x2 = int((s + 1) * step_w)
            dst_slice_w = max(1, dst_x2 - dst_x1)

            col = art_scaled.crop((src_x1, 0, src_x2, body_h))
            col_stretched = col.resize((dst_slice_w, body_h), Image.Resampling.BILINEAR)
            cylindrical_art.paste(col_stretched, (dst_x1, 0))

        # 4. Máscara com bordas suavemente arredondadas e perspectiva superior
        mask = Image.new("L", (body_w, body_h), 0)
        mdraw = ImageDraw.Draw(mask)
        mdraw.rounded_rectangle([(0, 0), (body_w, body_h)], radius=36, fill=255)

        # 5. Shading e Reflexo Cerâmico Esmaltado (Ceramic Glaze Highlights)
        shading = Image.new("RGBA", (body_w, body_h), (0, 0, 0, 0))
        shdraw = ImageDraw.Draw(shading)

        # Gradiente horizontal de iluminação
        for x in range(body_w):
            nx = x / body_w
            # Sombra suave na borda esquerda
            if nx < 0.12:
                alpha = int(90 * (1.0 - (nx / 0.12)))
                shdraw.line([(x, 0), (x, body_h)], fill=(15, 23, 42, alpha))
            # Brilho especular (reflexo de luz de estúdio em nx ~ 0.22)
            elif 0.14 <= nx <= 0.30:
                dist = abs(nx - 0.22) / 0.08
                if dist < 1.0:
                    alpha = int(75 * math.cos(dist * math.pi / 2.0))
                    shdraw.line([(x, 0), (x, body_h)], fill=(255, 255, 255, alpha))
            # Sombra na borda direita (curvatura para longe)
            elif nx > 0.85:
                alpha = int(120 * ((nx - 0.85) / 0.15))
                shdraw.line([(x, 0), (x, body_h)], fill=(15, 23, 42, alpha))

        # Compõe o cilindro sombreado
        shaded_art = Image.alpha_composite(cylindrical_art, shading)

        # Cola na imagem principal
        mug_img.paste(shaded_art, (body_x, body_y), mask)

        # 6. Borda do aro superior da caneca (Mug Rim)
        rim = Image.new("RGBA", (body_w, 36), (0, 0, 0, 0))
        rdraw = ImageDraw.Draw(rim)
        rdraw.ellipse([(0, 0), (body_w, 36)], fill=(255, 255, 255, 255), outline=(220, 226, 232, 255), width=3)
        mug_img.alpha_composite(rim, (body_x, body_y - 12))

        return mug_img

    @classmethod
    def process_mug_outputs(
        cls,
        source_image: Image.Image,
        base_name: str,
        output_dir: Path,
        generate_mockup: bool = False
    ) -> Dict[str, Path]:
        """
        Recebe a arte pronta da caneca (22x9.5cm @ 300 DPI) e gera:
        1. Versão Impressão Sublimática: Tratada termicamente para evitar sobrecarga e queima.
        2. Versão Prévia do Cliente: Visualização digital fiel calibrada para tela de celular.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        results = {}

        # 1. Impressão Sublimática (Ultra rápido: ~0.1s com LUT)
        print_sublimation_img = cls.prepare_for_sublimation(source_image)
        print_path = output_dir / f"{base_name}_impressao_sublimacao_300dpi.png"
        print_sublimation_img.save(print_path, "PNG", dpi=(cls.DPI, cls.DPI))
        results["print_sublimation"] = print_path

        # 2. Prévia do Cliente para aprovação (tela sRGB limpa)
        preview_img = cls.generate_client_preview(source_image, include_header=True)
        preview_path = output_dir / f"{base_name}_preview_cliente.png"
        preview_img.save(preview_path, "PNG", dpi=(cls.DPI, cls.DPI))
        results["client_preview"] = preview_path

        # 3. Mockup 3D (Desativado por padrão: economiza tempo e processamento)
        if generate_mockup:
            mockup_img = cls.generate_mug_3d_mockup(source_image, side="both")
            mockup_path = output_dir / f"{base_name}_mockup_caneca.png"
            mockup_img.save(mockup_path, "PNG", dpi=(cls.DPI, cls.DPI))
            results["mockup_3d"] = mockup_path

        return results

    @classmethod
    def _get_font(cls, name: str, size: int) -> ImageFont.FreeTypeFont:
        """Carrega fonte com fallbacks para Windows."""
        win_fonts = Path("C:/Windows/Fonts")
        mapping = {
            "segoe": "segoeui.ttf",
            "segoe_bold": "segoeuib.ttf",
            "segoe_italic": "segoeuii.ttf",
            "arial": "arial.ttf",
            "arial_bold": "arialbd.ttf",
        }
        fn = mapping.get(name.lower(), f"{name}.ttf")
        fp = win_fonts / fn
        if fp.exists():
            try:
                return ImageFont.truetype(str(fp), size)
            except Exception:
                pass
        for fb in ["segoeuib.ttf", "arialbd.ttf", "arial.ttf"]:
            fbp = win_fonts / fb
            if fbp.exists():
                try:
                    return ImageFont.truetype(str(fbp), size)
                except Exception:
                    pass
        return ImageFont.load_default()
