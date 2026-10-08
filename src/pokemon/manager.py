"""Gerenciador e orquestrador de arquivos para o perfil Pokémon Card."""

import json
from pathlib import Path
from typing import List, Optional, Tuple
from src.pokemon.schema import (
    AttackModel,
    CardStage,
    CardStyle,
    EnergyType,
    PokemonCardData,
)


class PokemonCardManager:
    """Gerencia a identificação, validação e carregamento de cartas de Pokémon."""

    @staticmethod
    def get_data_file_for_image(image_path: Path) -> Optional[Path]:
        """Procura o arquivo de metadados (.json, .txt, .yaml) com o mesmo nome base da imagem."""
        parent = image_path.parent
        stem = image_path.stem

        candidates = [
            parent / f"{stem}.json",
            parent / f"{stem}.txt",
            parent / f"{stem}.yaml",
            parent / f"{stem}.yml",
        ]
        for c in candidates:
            if c.exists() and c.is_file():
                return c
        return None

    @classmethod
    def load_card_for_image(cls, image_path: Path) -> PokemonCardData:
        """
        Carrega os dados da carta associados a uma imagem.
        Se nenhum arquivo existir, cria automaticamente uma ficha padrão coerente.
        """
        data_file = cls.get_data_file_for_image(image_path)
        if data_file:
            return PokemonCardData.from_file(data_file)

        # Fallback inteligente: cria dados básicos e salva um template para o usuário poder editar
        auto_name = image_path.stem.replace("_", " ").replace("-", " ").title()
        card = PokemonCardData(
            name=auto_name,
            stage=CardStage.BASIC,
            hp=100,
            energy_type=EnergyType.COLORLESS,
            style=CardStyle.MODERN,
            attacks=[
                AttackModel(
                    cost=[EnergyType.COLORLESS, EnergyType.COLORLESS],
                    name="Swift Impact",
                    damage="60",
                    description="This attack's damage isn't affected by Weakness or Resistance."
                )
            ],
            flavor_text=f"A rare custom edition of {auto_name} crafted for high-definition collectors."
        )

        # Salva o .json gerado para conveniência do usuário
        sample_path = image_path.parent / f"{image_path.stem}.json"
        try:
            sample_path.write_text(
                json.dumps(card.to_sample_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
        except Exception:
            pass

        return card

    @classmethod
    def create_sample_card_file(cls, target_dir: Path, name: str = "pikachu_sample") -> Tuple[Path, Path]:
        """Cria um arquivo de exemplo com dados completos para servir de guia ao usuário."""
        target_dir.mkdir(parents=True, exist_ok=True)
        json_file = target_dir / f"{name}.json"
        
        sample = PokemonCardData(
            name="Pikachu Special",
            stage=CardStage.BASIC,
            hp=120,
            energy_type=EnergyType.LIGHTNING,
            style=CardStyle.MODERN,
            pokedex_number="NO. 0025",
            species="Mouse Pokémon",
            height="1'04\"",
            weight="13.2 lbs",
            attacks=[
                AttackModel(
                    cost=[EnergyType.LIGHTNING],
                    name="Electro Ball",
                    damage="30",
                    description="Flip a coin. If heads, your opponent's Active Pokémon is now Paralyzed."
                ),
                AttackModel(
                    cost=[EnergyType.LIGHTNING, EnergyType.COLORLESS, EnergyType.COLORLESS],
                    name="Thunderbolt",
                    damage="90",
                    description="Discard all Energy attached to this Pokémon."
                )
            ],
            retreat_cost=1,
            rarity="Rare Holo",
            card_number="025/165",
            illustrator="Studio Kustom",
            flavor_text="When several of these Pokémon gather, their electricity can build and cause lightning storms."
        )

        json_file.write_text(
            json.dumps(sample.to_sample_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        return json_file, target_dir
