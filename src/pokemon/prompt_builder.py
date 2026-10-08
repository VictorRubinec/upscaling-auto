"""Gerador de Prompts Especializados para Criação de Cartas de Pokémon TCG via Gemini."""

from typing import Dict
from src.pokemon.schema import EnergyType, CardStyle, PokemonCardData


# Tabela oficial de cores de fundo e identidade visual por energia Pokémon
ENERGY_COLOR_MAP: Dict[EnergyType, Dict[str, str]] = {
    EnergyType.GRASS: {
        "color_name": "Forest Emerald Green",
        "hex": "#488f3e",
        "symbol_desc": "bright leaf symbol inside green circular orb",
        "bg_texture": "fine organic leaf pattern, emerald green gradient"
    },
    EnergyType.FIRE: {
        "color_name": "Crimson Fire Orange",
        "hex": "#e54222",
        "symbol_desc": "sharp flame flame symbol inside orange circular orb",
        "bg_texture": "warm ember radiant glow, fiery orange-red textured gradient"
    },
    EnergyType.WATER: {
        "color_name": "Azure Ocean Blue",
        "hex": "#3399cc",
        "symbol_desc": "crisp water droplet symbol inside deep blue circular orb",
        "bg_texture": "rippling aquatic sapphire waves, ocean blue gradient"
    },
    EnergyType.LIGHTNING: {
        "color_name": "Electric Yellow",
        "hex": "#f5bc14",
        "symbol_desc": "sharp lightning bolt inside golden yellow circular orb",
        "bg_texture": "dynamic electrical sparks, radiant golden-yellow gradient"
    },
    EnergyType.PSYCHIC: {
        "color_name": "Mystic Violet Purple",
        "hex": "#7d4486",
        "symbol_desc": "stylized psychic eye inside purple circular orb",
        "bg_texture": "mystic cosmic vortex, deep violet amethyst glow"
    },
    EnergyType.FIGHTING: {
        "color_name": "Earthy Terra Cotta Clay",
        "hex": "#b4572c",
        "symbol_desc": "white fist symbol inside brown-orange circular orb",
        "bg_texture": "weathered cracked stone, warm ochre granite texture"
    },
    EnergyType.DARKNESS: {
        "color_name": "Deep Shadow Indigo",
        "hex": "#2e3b4e",
        "symbol_desc": "sharp crescent claw inside dark indigo circular orb",
        "bg_texture": "obsidian shadows, dark starry nebulas"
    },
    EnergyType.METAL: {
        "color_name": "Brushed Chrome Silver",
        "hex": "#7f939e",
        "symbol_desc": "steel bolt hexagon inside metallic silver circular orb",
        "bg_texture": "brushed steel plate, sleek metallic silver texture"
    },
    EnergyType.FAIRY: {
        "color_name": "Pastel Magenta Pink",
        "hex": "#d34289",
        "symbol_desc": "fairy wing silhouette inside luminous pink circular orb",
        "bg_texture": "fairy dust glitter, soft pink radiant bokeh"
    },
    EnergyType.DRAGON: {
        "color_name": "Dragon Gold Bronze",
        "hex": "#9c812d",
        "symbol_desc": "dragon dragon fang insignia inside antique gold circular orb",
        "bg_texture": "ancient dragon scales, deep gold and bronze metallic sheen"
    },
    EnergyType.COLORLESS: {
        "color_name": "Neutral Pearl White",
        "hex": "#c4c4c4",
        "symbol_desc": "six-pointed star inside pearlescent white circular orb",
        "bg_texture": "smooth pearlescent silver-white fine canvas"
    },
}


class PokemonCardPromptBuilder:
    """Constrói o prompt mestre para o modelo de IA gerar o design completo da carta Pokémon."""

    @staticmethod
    def build_prompt(card: PokemonCardData) -> str:
        """
        Monta uma especificação técnica rigorosa em formato estruturado para o Gemini Vision,
        garantindo a reprodução fiel do layout, tipografia e anatomia oficial de Pokémon TCG.
        """
        energy_info = ENERGY_COLOR_MAP.get(
            card.energy_type,
            ENERGY_COLOR_MAP[EnergyType.COLORLESS]
        )

        # Formatação dos ataques
        attacks_formatted = []
        for atk in card.attacks:
            cost_symbols = ", ".join([f"[{c.value} Energy Orb]" for c in atk.cost])
            damage_str = f" | Damage: {atk.damage}" if atk.damage else ""
            desc_str = f"\n      * Effect: \"{atk.description}\"" if atk.description else ""
            attacks_formatted.append(
                f"    - Cost: {cost_symbols} | Name: \"{atk.name}\"{damage_str}{desc_str}"
            )
        attacks_text = "\n".join(attacks_formatted) if attacks_formatted else "    - Cost: [Colorless Energy Orb] | Name: Tackle | Damage: 30"

        # Habilidade (opcional)
        ability_block = ""
        if card.ability:
            ability_block = (
                f"\n  * SPECIAL ABILITY:\n"
                f"    - Badge: Red rectangular rounded badge reading 'ABILITY' in bold white capital letters\n"
                f"    - Name: \"{card.ability.name}\" in dark bold text\n"
                f"    - Description: \"{card.ability.description}\" in crisp regular text\n"
            )

        # Batalha e Fraqueza
        weakness_str = f"[{card.weakness.type.value} Orb] {card.weakness.value}" if card.weakness else "None"
        resistance_str = f"[{card.resistance.type.value} Orb] {card.resistance.value}" if card.resistance else "None"
        retreat_orbs = " ".join(["[Colorless Orb]"] * card.retreat_cost) if card.retreat_cost > 0 else "None"

        # Variação do estilo de moldura
        if card.style == CardStyle.CLASSIC:
            border_instruction = (
                "CLASSIC RETRO ERA (Base Set Style):\n"
                "- Border: Classic 3.5mm solid canary-yellow outer border with rounded corners.\n"
                "- Artwork Window: Defined rectangular window with a 3D beveled metallic golden frame in the upper half.\n"
                "- Background: Vintage subtle textured parchment gradient matching the Pokémon's elemental type."
            )
        elif card.style == CardStyle.FULL_ART:
            border_instruction = (
                "SPECIAL ILLUSTRATION RARE / FULL ART TCG MASTERWORK STYLE:\n"
                "- Canvas Coverage: 100% borderless FULL-BLEED artwork. The character illustration and surrounding atmospheric scenery seamlessly expand to all four outer edges of the physical card, with NO thick outer borders and NO rectangular picture frame.\n"
                "- UI Layering (Floating Glassmorphism): All gameplay UI elements (Header, Ability pill, Attack boxes, and Bottom Stats) are designed as sleek, floating, semi-transparent frosted-glass overlay containers (subtle backdrop-blur, faint luminous contour lines, and soft ambient drop shadows) so the breathtaking character art remains fully visible beneath while maintaining razor-sharp text legibility.\n"
                "- Character Dominance: The Pokémon/characters dynamically break across the foreground and midground in cinematic grandeur, interacting with light rays, elemental particles, and atmospheric depth.\n"
                "- Premium Rarity Finish: Subtle holographic sheen accents, iridescent highlights, and official Special Illustration Rare golden twin stars (★★) in the collector footer."
            )
        else:  # Modern (Scarlet & Violet)
            border_instruction = (
                "MODERN OFFICIAL TCG STYLE (Scarlet & Violet / Sword & Shield Era):\n"
                "- Border: Refined metallic brushed-silver border (2.5mm width) with precise rounded card corners.\n"
                "- Artwork Window: Centered high-definition artwork container occupying the upper 45% of the card with subtle holographic foil bevel edges.\n"
                "- Background: Crisp modern elemental texture themed to the energy type."
            )

        # Dados da Pokédex
        pokedex_line = ""
        if card.species or card.pokedex_number or card.height or card.weight:
            parts = []
            if card.pokedex_number:
                parts.append(card.pokedex_number)
            if card.species:
                parts.append(card.species)
            if card.height:
                parts.append(f"HT: {card.height}")
            if card.weight:
                parts.append(f"WT: {card.weight}")
            pokedex_str = "  ".join(parts)
            pokedex_line = (
                f"- POKÉDEX DATA STRIP (Right below the artwork frame):\n"
                f"  A thin golden/bronze decorative horizontal banner containing italicized micro-text: \"{pokedex_str}\".\n"
            )

        prompt = f"""You are the master Art Director and Chief Graphic Designer for the official Pokémon Trading Card Game (TCG).

MISSION:
Take the provided character artwork in the attachment and integrate it into a complete, pristine, broadcast-quality official Pokémon Trading Card design ready for physical 300+ DPI micro-printing.

STRICT TECHNICAL SPECIFICATIONS:
- Physical Dimensions: 63.5 x 88.9 mm (Standard 2.5 x 3.5 inches trading card proportion).
- Aspect Ratio: Exactly 1:1.4 vertical orientation (no letterboxing, no horizontal stretching).
- Typography & Fonts: Must use the authentic Pokémon TCG typography system (Gill Sans Bold / Futura Condensed Bold for headers, Futura Demi for numbers, and crisp legible sans-serif for rule texts).
- Resolution: Absolute highest definition, ultra-sharp vector-like edge rendering, zero blurry letters, zero garbled text. Every single letter and number must be spelled with 100% orthographic perfection.

CARD DESIGN STYLE & AESTHETIC:
{border_instruction}

PRIMARY ELEMENTAL THEME:
- Element: {card.energy_type.value} ({energy_info['color_name']})
- Color Palette: {energy_info['hex']} base tones, accompanied by {energy_info['bg_texture']}
- Energy Symbol: {energy_info['symbol_desc']}

CARD ANATOMY & ELEMENT PLACEMENT:

1. TOP HEADER BAR:
   - Top-Left: Small stage indicator tag reading "{card.stage.value.upper()}"{f' (Evolves from {card.evolves_from})' if card.evolves_from else ''}.
   - Pokémon Name: "{card.name}" in large, prominent, ultra-clean Gill Sans bold typography.
   - Top-Right: HP display reading "{card.hp} HP" in bold dark typography, immediately followed by the circular {card.energy_type.value} Energy Orb symbol.

2. ARTWORK INTEGRATION:
   - Use the uploaded character illustration as the hero artwork.
   - Maintain the character's exact visual style, proportions, and lighting while seamlessly harmonizing it into the card frame.

3. {pokedex_line}
4. ABILITIES & ATTACKS SECTION (Middle to lower-center container):
{ability_block}
  * ATTACKS:
{attacks_text}
   - Layout rule: The circular energy cost orbs MUST be aligned to the far left. The Attack Name must be in bold. The Damage number (if applicable) MUST be right-aligned on the exact same line. The attack effect description must be neatly formatted below.

5. BOTTOM BATTLE STATS BAR:
   - Three balanced columns in a slim light-gray/silver horizontal bar:
     * Weakness: {weakness_str}
     * Resistance: {resistance_str}
     * Retreat Cost: {retreat_orbs}

6. LEGAL & COLLECTOR FOOTER:
   - Left side: "Illus. {card.illustrator}" in fine 6pt sans-serif text.
   - Center/Right side: "{card.flavor_text or 'Created for collectors'}" (in fine italic script) or collector number "{card.card_number}" alongside the official {card.rarity} icon (Holo Star symbol).
   - Bottom margin: "© Pokémon / Nintendo / Creatures / GAME FREAK / Studio Kustom".

CRITICAL QUALITY DIRECTIVES:
- Do NOT hallucinate deformed symbols or unreadable glyphs.
- All numbers ({card.hp} HP, damage values, retreat cost) must be razor sharp and legible even at thumbnail scale.
- Output ONLY the finished front-face card graphic, perfectly centered and framed without mockup angles, fingers, desks, or perspective skewing.
"""
        return prompt.strip()
