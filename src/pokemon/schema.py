import json
import re
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EnergyType(str, Enum):
    """Tipos de energia e elementos oficiais do Pokémon TCG."""
    GRASS = "Grass"
    FIRE = "Fire"
    WATER = "Water"
    LIGHTNING = "Lightning"
    PSYCHIC = "Psychic"
    FIGHTING = "Fighting"
    DARKNESS = "Darkness"
    METAL = "Metal"
    FAIRY = "Fairy"
    DRAGON = "Dragon"
    COLORLESS = "Colorless"


class CardStage(str, Enum):
    """Estágios evolutivos de cartas Pokémon."""
    BASIC = "Basic"
    STAGE_1 = "Stage 1"
    STAGE_2 = "Stage 2"
    POKEMON_EX = "Pokémon ex"
    POKEMON_V = "Pokémon V"
    POKEMON_VMAX = "Pokémon VMAX"
    POKEMON_VSTAR = "Pokémon VSTAR"


class CardStyle(str, Enum):
    """Estilos e eras visuais do design das cartas."""
    MODERN = "modern"        # Scarlet & Violet / Sword & Shield (bordas metálicas/prateadas)
    CLASSIC = "classic"      # Base Set WOTC (bordas amarelas icônicas, moldura clássica)
    FULL_ART = "full_art"    # Arte completa sangrada ocupando todo o card com UI translúcida


class AttackModel(BaseModel):
    """Representa um ataque na carta Pokémon."""
    cost: List[EnergyType] = Field(
        default_factory=lambda: [EnergyType.COLORLESS],
        description="Lista de tipos de energia necessários para o ataque."
    )
    name: str = Field(..., description="Nome do ataque.")
    damage: str = Field(default="", description="Valor de dano (ex: '30', '90+', '120x').")
    description: str = Field(default="", description="Efeito ou texto de regra do ataque.")


class WeaknessResistanceModel(BaseModel):
    """Modelagem de Fraqueza ou Resistência."""
    type: EnergyType
    value: str = "x2"


class AbilityModel(BaseModel):
    """Representa uma Habilidade especial (Ability / Poké-Power)."""
    name: str
    description: str


class PokemonCardData(BaseModel):
    """Ficha técnica estruturada de uma carta Pokémon colecionável."""
    name: str = Field(..., description="Nome do Pokémon ou personagem.")
    stage: CardStage = Field(default=CardStage.BASIC, description="Estágio evolutivo.")
    evolves_from: Optional[str] = Field(default=None, description="Nome do Pokémon anterior do qual este evolui.")
    hp: int = Field(default=100, ge=10, le=400, description="Pontos de vida (HP).")
    energy_type: EnergyType = Field(default=EnergyType.COLORLESS, description="Tipo elementar principal da carta.")
    
    # Informações da Pokédex (sub-barra da ilustração)
    pokedex_number: Optional[str] = Field(default=None, description="Número na Pokédex (ex: 'NO. 0025').")
    species: Optional[str] = Field(default=None, description="Espécie ou categoria (ex: 'Mouse Pokémon').")
    height: Optional[str] = Field(default=None, description="Altura (ex: '1\\'04\"' ou '0.4 m').")
    weight: Optional[str] = Field(default=None, description="Peso (ex: '13.2 lbs' ou '6.0 kg').")
    
    # Habilidade (opcional)
    ability: Optional[AbilityModel] = None
    
    # Ataques
    attacks: List[AttackModel] = Field(default_factory=list, description="Lista de 1 a 2 ataques.")
    
    # Batalha e Custos de Rodapé
    weakness: Optional[WeaknessResistanceModel] = None
    resistance: Optional[WeaknessResistanceModel] = None
    retreat_cost: int = Field(default=1, ge=0, le=5, description="Quantidade de energias de custo de recuo.")
    
    # Metadados de Coleção e Impressão
    rarity: str = Field(default="Rare Holo", description="Raridade da carta.")
    card_number: str = Field(default="001/100", description="Numeração da carta na coleção.")
    illustrator: str = Field(default="Studio Kustom", description="Nome do artista/ilustrador.")
    flavor_text: Optional[str] = Field(default=None, description="Texto descritivo ou citação da Pokédex.")
    
    # Estilo visual de design
    style: CardStyle = Field(default=CardStyle.MODERN, description="Estilo visual da moldura e tipografia.")

    @classmethod
    def from_file(cls, path: Path) -> "PokemonCardData":
        """Carrega e valida os dados de um arquivo .json ou .txt."""
        suffix = path.suffix.lower()
        if suffix == ".json":
            content = json.loads(path.read_text(encoding="utf-8"))
            return cls.model_validate(content)
        elif suffix in (".txt", ".yaml", ".yml"):
            return cls._from_text_kv(path.read_text(encoding="utf-8"), fallback_name=path.stem)
        else:
            raise ValueError(f"Formato de arquivo não suportado para dados de Pokémon: {suffix}")

    @classmethod
    def _from_text_kv(cls, text: str, fallback_name: str) -> "PokemonCardData":
        """Analisa um arquivo de texto simples no formato chave: valor."""
        lines = [line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith("#")]
        data: Dict[str, Any] = {"name": fallback_name, "attacks": []}

        for line in lines:
            if ":" not in line:
                continue
            key, val = line.split(":", 1)
            key = key.strip().lower()
            val = val.strip()

            if key in ("name", "nome"):
                data["name"] = val
            elif key in ("hp", "vida"):
                nums = re.findall(r"\d+", val)
                if nums:
                    data["hp"] = int(nums[0])
            elif key in ("type", "tipo", "energy"):
                for t in EnergyType:
                    if t.value.lower() == val.lower():
                        data["energy_type"] = t.value
                        break
            elif key in ("stage", "estagio"):
                for s in CardStage:
                    if s.value.lower() == val.lower():
                        data["stage"] = s.value
                        break
            elif key in ("evolves_from", "evolui_de"):
                data["evolves_from"] = val
            elif key in ("pokedex", "pokedex_number", "numero"):
                data["pokedex_number"] = val
            elif key in ("species", "especie"):
                data["species"] = val
            elif key in ("attack", "ataque", "attack1", "ataque1"):
                # Exemplo: "Lightning: Spark: 30: Does 10 damage to bench"
                parts = [p.strip() for p in val.split(":")]
                if len(parts) >= 2:
                    cost_type = parts[0]
                    atk_name = parts[1]
                    atk_dmg = parts[2] if len(parts) > 2 else ""
                    atk_desc = parts[3] if len(parts) > 3 else ""
                    data["attacks"].append({
                        "cost": [cost_type] if cost_type in EnergyType.__members__ else ["Colorless"],
                        "name": atk_name,
                        "damage": atk_dmg,
                        "description": atk_desc
                    })
            elif key in ("retreat", "retreat_cost", "recuo"):
                nums = re.findall(r"\d+", val)
                if nums:
                    data["retreat_cost"] = int(nums[0])
            elif key in ("illustrator", "ilustrador", "artist"):
                data["illustrator"] = val
            elif key in ("flavor_text", "flavor", "descricao"):
                data["flavor_text"] = val
            elif key in ("style", "estilo"):
                for st in CardStyle:
                    if st.value.lower() == val.lower():
                        data["style"] = st.value
                        break

        if not data["attacks"]:
            data["attacks"].append({
                "cost": ["Colorless"],
                "name": "Custom Strike",
                "damage": "50",
                "description": "A powerful custom attack created with precision."
            })

        return cls.model_validate(data)

    def to_sample_dict(self) -> dict:
        """Gera um dicionário modelo completo pronto para ser salvo como .json de exemplo."""
        return {
            "name": self.name,
            "stage": self.stage.value,
            "evolves_from": self.evolves_from,
            "hp": self.hp,
            "energy_type": self.energy_type.value,
            "style": self.style.value,
            "pokedex_number": self.pokedex_number or "NO. 0000",
            "species": self.species or "Custom Pokémon",
            "height": self.height or "1'00\"",
            "weight": self.weight or "10.0 lbs",
            "ability": {
                "name": self.ability.name,
                "description": self.ability.description
            } if self.ability else None,
            "attacks": [
                {
                    "cost": [c.value for c in atk.cost],
                    "name": atk.name,
                    "damage": atk.damage,
                    "description": atk.description
                }
                for atk in self.attacks
            ],
            "weakness": {
                "type": self.weakness.type.value if self.weakness else "Fighting",
                "value": self.weakness.value if self.weakness else "x2"
            },
            "resistance": {
                "type": self.resistance.type.value if self.resistance else "Metal",
                "value": self.resistance.value if self.resistance else "-20"
            } if self.resistance else None,
            "retreat_cost": self.retreat_cost,
            "rarity": self.rarity,
            "card_number": self.card_number,
            "illustrator": self.illustrator,
            "flavor_text": self.flavor_text or "A uniquely designed collectible card created for high-definition physical printing."
        }
