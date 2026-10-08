import json
import logging
from pathlib import Path
from typing import Optional, Union, Dict, Any

from src.tcg.onepiece.schema import (
    OnePieceCardData,
    OpColor,
    CardCategory,
    AttributeType,
    OpCardStyle,
    OpRarity,
)

logger = logging.getLogger("GeminiUpscaler.OnePieceManager")


class OnePieceCardManager:
    """Gerencia o ciclo de vida, arquivos de dados e templates de One Piece Card Game."""

    SUPPORTED_EXTENSIONS = (".json", ".yaml", ".yml", ".txt")

    @classmethod
    def find_data_file(cls, image_path: Path) -> Optional[Path]:
        """Localiza o arquivo de dados correspondente à imagem na mesma pasta."""
        folder = image_path.parent
        stem = image_path.stem

        # Padrões de busca por prioridade
        candidates = [
            folder / f"{stem}.json",
            folder / f"{stem}.yaml",
            folder / f"{stem}.yml",
            folder / f"{stem}.txt",
            folder / f"{stem}_onepiece.json",
            folder / f"{stem}_opcg.json",
            folder / "card.json",
            folder / "ficha.json",
        ]

        for cand in candidates:
            if cand.exists() and cand.is_file():
                return cand

        return None

    @classmethod
    def parse_data_file(cls, file_path: Path) -> Dict[str, Any]:
        """Lê e converte arquivo JSON, YAML ou TXT chave-valor em dicionário."""
        content = file_path.read_text(encoding="utf-8").strip()

        if file_path.suffix.lower() == ".json":
            return json.loads(content)

        if file_path.suffix.lower() in (".yaml", ".yml"):
            try:
                import yaml
                return yaml.safe_load(content) or {}
            except ImportError:
                logger.warning("PyYAML não instalado. Tentando parse básico de JSON.")
                return json.loads(content)

        # Fallback TXT chave: valor
        data = {}
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                k, v = line.split(":", 1)
                data[k.strip().lower()] = v.strip()
        return data

    @classmethod
    def load_card_for_image(cls, image_path: Path) -> OnePieceCardData:
        """Carrega a ficha técnica associada ou gera uma versão padrão de alta qualidade."""
        data_file = cls.find_data_file(image_path)
        if data_file:
            try:
                raw_dict = cls.parse_data_file(data_file)
                return OnePieceCardData.from_dict(raw_dict)
            except Exception as e:
                logger.warning(f"Erro ao ler ficha '{data_file.name}': {e}. Usando configuração padrão.")

        # Fallback automático baseado no nome do arquivo
        clean_name = image_path.stem.replace("_", " ").replace("-", " ").title()
        return OnePieceCardData(
            name=clean_name,
            category=CardCategory.CHARACTER,
            color=OpColor.RED,
            cost=5,
            power=6000,
            counter=1000,
            attribute=AttributeType.STRIKE,
            affiliations=["Straw Hat Crew"],
            effect="[On Play] Se o seu Líder for do bando dos Chapéus de Palha, este personagem ganha +2000 de Poder até o final do turno.",
            trigger=None,
            card_code="OP05-001",
            rarity=OpRarity.SR,
            style=OpCardStyle.MANGA_ALT_ART,
            illustrator="Studio Kustom",
            flavor_quote="O lado bom da vida é o que tem você comigo."
        )

    @classmethod
    def create_template_file(cls, target_dir: Path, name: str = "luffy") -> Path:
        """Gera um arquivo JSON de exemplo pronto para edição."""
        target_path = target_dir / f"{name}.json"
        sample_card = OnePieceCardData(
            name="Monkey D. Luffy",
            category=CardCategory.CHARACTER,
            color=OpColor.RED,
            cost=5,
            power=6000,
            counter=1000,
            attribute=AttributeType.STRIKE,
            affiliations=["Supernovas", "Straw Hat Crew"],
            effect="[DON!! x1] [When Attacking] Este personagem ganha [Rush] e não pode ser bloqueado por personagens com 4000 ou menos de poder durante esta batalha.",
            trigger="[Trigger] Compre 1 carta da sua pilha de Vida e jogue este personagem se você tiver 2 ou menos cartas na mão.",
            card_code="OP05-119",
            rarity=OpRarity.SEC,
            style=OpCardStyle.MANGA_ALT_ART,
            illustrator="Studio Kustom",
            flavor_quote="Eu serei o Rei dos Piratas!"
        )
        target_path.write_text(json.dumps(sample_card.model_dump(), indent=2, ensure_ascii=False), encoding="utf-8")
        return target_path
