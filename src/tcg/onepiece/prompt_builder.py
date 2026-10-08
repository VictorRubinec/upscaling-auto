from typing import Dict, Any
from src.tcg.onepiece.schema import (
    OnePieceCardData,
    OpColor,
    CardCategory,
    AttributeType,
    OpCardStyle,
    OpRarity,
)


class OnePiecePromptBuilder:
    """
    Construtor de prompts de alta fidelidade técnica para geração e upscaling
    de cartas de One Piece Card Game (Bandai) no Gemini Vision.
    """

    COLOR_PALETTES: Dict[OpColor, Dict[str, str]] = {
        OpColor.RED: {
            "name": "Red (Fiery Will / Aggro)",
            "primary_hex": "#E11D48",
            "accent_hex": "#FFE4E6",
            "theme": "vivid crimson red with fiery ember textures and high-contrast bold energy",
        },
        OpColor.GREEN: {
            "name": "Green (Wano / East Blue)",
            "primary_hex": "#059669",
            "accent_hex": "#D1FAE5",
            "theme": "emerald forest green with sharp bamboo and wind-blade nautical patterns",
        },
        OpColor.BLUE: {
            "name": "Blue (Seven Warlords / Marine)",
            "primary_hex": "#0284C7",
            "accent_hex": "#E0F2FE",
            "theme": "deep sapphire ocean blue with swirling cresting wave foam and tidal currents",
        },
        OpColor.PURPLE: {
            "name": "Purple (Animal Kingdom / Film)",
            "primary_hex": "#7C3AED",
            "accent_hex": "#EDE9FE",
            "theme": "dark royal imperial purple with toxic lightning flares and dark aura particles",
        },
        OpColor.BLACK: {
            "name": "Black (CP9 / Dressrosa / Navy)",
            "primary_hex": "#1E293B",
            "accent_hex": "#F1F5F9",
            "theme": "sleek obsidian black and dark slate with smoke, shadow tendrils, and silver chrome accents",
        },
        OpColor.YELLOW: {
            "name": "Yellow (Big Mom / Land of Wano)",
            "primary_hex": "#EAB308",
            "accent_hex": "#FEF9C3",
            "theme": "electric solar gold and citrus yellow with sunbeam flares and celestial halo glows",
        },
        OpColor.MULTI: {
            "name": "Multi-Color Dual Faction",
            "primary_hex": "#C026D3",
            "accent_hex": "#FAE8FF",
            "theme": "dual-split harmonious elemental gradients with metallic golden dividers",
        },
    }

    @classmethod
    def build_prompt(cls, card: OnePieceCardData) -> str:
        """Gera o prompt em inglês técnico para sintetizar a carta oficial de One Piece TCG."""
        palette = cls.COLOR_PALETTES.get(card.color, cls.COLOR_PALETTES[OpColor.RED])
        
        # Formatação das Afiliações (ex: "Straw Hat Crew / Supernovas")
        affiliations_str = " / ".join(card.affiliations) if card.affiliations else "Pirates"

        # Custo ou Vida (Leader vs Character)
        if card.category == CardCategory.LEADER:
            cost_header = (
                f"- LEADER LIFE INDICATOR (Top-Left):\n"
                f"  A large embossed golden shield badge containing the bold text: \"LIFE: {card.life or 5}\"."
            )
        else:
            cost_header = (
                f"- DON!! COST OCTAGON (Top-Left):\n"
                f"  A beveled golden 3D octagon frame containing the numeral \"{card.cost if card.cost is not None else 5}\" "
                f"in heavy bold typography with a radiant inner glow."
            )

        # Atributo de Combate (Slash, Strike, etc.)
        attribute_desc = "None"
        if card.attribute:
            attr_icons = {
                AttributeType.SLASH: "a crossed curved katana blade silhouette",
                AttributeType.STRIKE: "a powerful clenched gauntlet / fist impact silhouette",
                AttributeType.RANGED: "a crosshair target / flintlock pistol silhouette",
                AttributeType.SPECIAL: "a swirling mystique devil-fruit spiral icon",
                AttributeType.WISDOM: "an open ancient parchment scroll / quill icon",
            }
            attribute_desc = (
                f"- COMBAT ATTRIBUTE BADGE (Top-Right):\n"
                f"  A circular icon badge displaying {attr_icons.get(card.attribute, 'combat symbol')} "
                f"with the clean label: \"{card.attribute.value.upper()}\"."
            )

        # Poder e Contra-Ataque (Power & Counter)
        combat_stats_block = ""
        if card.power is not None:
            combat_stats_block += (
                f"- POWER NUMERALS (Middle-Right):\n"
                f"  Prominent vertical or horizontal display reading \"POWER: {card.power}\" in ultra-bold condensed Shonen lettering.\n"
            )
        if card.counter is not None and card.counter > 0:
            combat_stats_block += (
                f"- COUNTER BADGE (Middle-Left Border):\n"
                f"  A sleek horizontal banner badge displaying \"COUNTER +{card.counter}\" with defensive shield bevels.\n"
            )

        # Trigger (opcional)
        trigger_block = ""
        if card.trigger:
            trigger_block = (
                f"\n  * TRIGGER STRIP (Bottom of effect box):\n"
                f"    - Banner: Glowing bright golden-yellow horizontal ribbon with a distinct red badge reading '[Trigger]'.\n"
                f"    - Trigger Effect Text: \"{card.trigger}\" in crisp dark bold lettering.\n"
            )

        # Estilo de Moldura (Standard, Extended, Manga Alt-Art)
        if card.style == OpCardStyle.MANGA_ALT_ART:
            style_instruction = (
                "SUPER PARALLEL / MANGA RARE MASTERPIECE STYLE (Manga Alt-Art):\n"
                "- Canvas & Bleed: 100% borderless FULL-BLEED artwork expanding seamlessly to all four physical edges of the card.\n"
                "- Background Layer: Iconic textured black-and-white manga action panels (komanwari layout), comic speed lines, half-tone screen dot shading, and dynamic Japanese sound effect onomatopoeia (SFX / 'DON!!' / 'どん!!') echoing the manga's most climactic panels.\n"
                "- Foreground Layer: The central character from the attachment rendered in vivid, saturated, full-color 3D grandeur, bursting out dynamically from the manga panels into the foreground with cinematic lighting, depth-of-field, and energetic particle sparks.\n"
                "- UI Layering: All gameplay UI containers (Cost octagon, Card Name, and Bottom Effect Box) are designed as floating, semi-transparent frosted-glass acrylic overlays with luminous edge bevels so the manga background and character remain visible underneath without compromising text sharpness.\n"
                "- Finish: Golden twin stars (★★) Super Parallel rarity mark and official gold foil accentuation."
            )
        elif card.style == OpCardStyle.EXTENDED:
            style_instruction = (
                "PARALLEL ART / WINNER EXTENDED STYLE:\n"
                "- Canvas & Bleed: Extended borderless illustration where the character dynamically breaks past traditional frame borders.\n"
                "- Accents: Golden embossed nautical corner flourishes, compass roses, and semi-translucent lower rule boxes allowing artwork to show through."
            )
        else:  # Standard
            style_instruction = (
                f"OFFICIAL STANDARD BANDAI ONE PIECE TCG STYLE:\n"
                f"- Border: High-impact solid outer border ({palette['primary_hex']}) themed to {palette['name']}.\n"
                f"- Artwork Window: Defined high-definition manga illustration container framed with engraved nautical rope and pirate helm motifs.\n"
                f"- Texture: {palette['theme']}."
            )

        prompt = f"""You are the Chief Graphic Designer and Art Director for the official Bandai ONE PIECE CARD GAME (OPCG).

MISSION:
Transform the character art provided in the attachment into a 100% authentic, broadcast-grade official One Piece Trading Card Game design ready for physical 300+ DPI micro-printing.

STRICT TECHNICAL SPECIFICATIONS:
- Physical Dimensions: 63.5 x 88.9 mm (Official 2.5 x 3.5 inches trading card proportions).
- Aspect Ratio: Exactly 1:1.4 vertical orientation (no letterboxing, no horizontal stretching, no black bars).
- Typography & Fonts: Must use the authentic One Piece TCG typography system (Impact / Futura Condensed Bold / Gotham Bold for titles, power numbers, and keyword badges; crisp geometric sans-serif for rule effects).
- Resolution & Edge Definition: Absolute highest resolution, razor-sharp vector-like edge rendering, zero blurry letters, zero garbled text. Every single character and number must be spelled with 100% orthographic perfection.

CARD AESTHETIC & FRAME STYLE:
{style_instruction}

FACTION & COLOR IDENTITY:
- Color: {palette['name']} ({palette['primary_hex']})
- Accent Tone: {palette['accent_hex']}

CARD ANATOMY & ELEMENT PLACEMENT:

1. TOP HEADER & ATTRIBUTES:
{cost_header}
{attribute_desc}
- CARD TITLE:
  \"{card.name.upper()}\" rendered in huge, commanding bold typography with a subtle dark outline and metallic drop-shadow.

2. COMBAT STATS:
{combat_stats_block}

3. LOWER TEXT BOX & RULES:
- AFFILIATIONS & TYPE BAR:
  A clean horizontal pill banner reading: \"{card.category.value.upper()} | {affiliations_str}\" in crisp white lettering over a dark acrylic backing.
- EFFECT RULES CONTAINER:
  Crisp container containing the exact effect rules:
  \"{card.effect}\"
  (Make sure official bracketed tags like '[DON!! x1]', '[On Play]', '[When Attacking]', '[Activate: Main]', '[Blocker]' or '[Rush]' appear as distinct high-contrast colored graphic badges).{trigger_block}

4. COLLECTOR FOOTER (Bottom Margin):
- Card Code & Rarity: \"{card.card_code} {card.rarity.value}\" in bottom-right corner.
- Illustrator Credit: \"Illus. {card.illustrator}\" in bottom-left corner.
- Copyright Line: \"© Eiichiro Oda / Shueisha, Toei Animation  BANDAI MADE IN JAPAN\" in microscopic crisp sub-text.
{f'- FLAVOR QUOTE: Italicized dramatic catchphrase: \"{card.flavor_quote}\"' if card.flavor_quote else ''}

STRICT EXCLUSIONS:
- DO NOT generate browser windows, mobile screen mockups, hands holding the card, or 3D tabletop surfaces.
- Generate EXCLUSIVELY the flat, pristine 2D printable trading card front face with precisely rounded die-cut corners.
"""
        return prompt.strip()
