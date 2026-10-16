"""Gerenciador e orquestrador de arquivos para o perfil Caneca de Cerâmica (MUG)."""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from src.mug.composer import MugComposerEngine
from src.mug.schema import MugArtConfig, MugLayoutType, MugPhotoConfig, MugTextConfig, MugBackgroundConfig


class MugManager:
    """Orquestrador de arquivos, templates e renderização de artes de canecas."""

    @staticmethod
    def get_mug_input_dir(base_data_dir: Path) -> Path:
        p = base_data_dir / "input" / "mug"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @staticmethod
    def get_mug_output_dir(base_data_dir: Path) -> Path:
        p = base_data_dir / "output" / "mug"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @classmethod
    def create_template(
        cls,
        base_data_dir: Path,
        name: str,
        layout: MugLayoutType = MugLayoutType.PHOTO_AND_TEXT
    ) -> Path:
        """Gera um arquivo modelo de configuração JSON com exemplo para o usuário preencher."""
        in_dir = cls.get_mug_input_dir(base_data_dir)
        clean_name = name.replace(".json", "")
        target_json = in_dir / f"{clean_name}.json"

        tmpl = MugArtConfig.sample_template(layout=layout)
        tmpl.title = clean_name.replace("_", " ").title()
        tmpl.save(target_json)
        return target_json

    @classmethod
    def load_config_for_image_or_dir(cls, path: Path) -> Optional[MugArtConfig]:
        """Tenta carregar o arquivo de configuração associado a uma imagem ou pasta."""
        if path.is_dir():
            for c_name in ["config.json", "mug.json", f"{path.name}.json"]:
                c_path = path / c_name
                if c_path.exists():
                    return MugArtConfig.from_file(c_path)
            return None

        # Se for um arquivo de imagem
        parent = path.parent
        candidates = [
            parent / f"{path.stem}.json",
            parent / "config.json",
            parent / "mug.json",
        ]
        for c in candidates:
            if c.exists():
                try:
                    return MugArtConfig.from_file(c)
                except Exception:
                    pass

        # Cria uma configuração padrão rápida para a foto avulsa
        return MugArtConfig(
            title=path.stem.replace("_", " ").title(),
            layout=MugLayoutType.PHOTO_AND_TEXT,
            background=MugBackgroundConfig(
                color="#F8FAFC",
                gradient_to="#E2E8F0",
                blur_source_photo=False,
            ),
            photos=[
                MugPhotoConfig(file=path.name, position="left")
            ],
            texts=[]
        )

    @classmethod
    def process_composition(
        cls,
        config: MugArtConfig,
        output_file: Path,
        base_dir: Optional[Path] = None,
        generate_proof: bool = True
    ) -> Tuple[Path, Optional[Path]]:
        """Executa a renderização do motor gráfico e salva os arquivos finais a 300 DPI."""
        output_file.parent.mkdir(parents=True, exist_ok=True)

        final_art, proof_art = MugComposerEngine.render_art(
            config=config,
            base_dir=base_dir,
            generate_proof=generate_proof
        )

        # Salva em alta resolução a 300 DPI
        final_art.save(output_file, "PNG", dpi=(300, 300))

        proof_path = None
        if proof_art and generate_proof:
            proof_path = output_file.with_name(f"{output_file.stem}_proof.png")
            proof_art.save(proof_path, "PNG", dpi=(300, 300))

        return output_file, proof_path
