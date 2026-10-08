"""Testes e verificação do gerador de cartas Pokémon."""

from pathlib import Path
from src.config import PRODUCT_REGISTRY, ProductType
from src.pokemon import (
    PokemonCardManager,
    PokemonCardPromptBuilder,
    PokemonCardData,
    CardStyle,
    EnergyType,
)


def test_schema_and_prompt():
    json_path = Path("data/input/pokemon_card/exemplo_pikachu.json")
    card = PokemonCardData.from_file(json_path)

    assert card.name == "Pikachu Special"
    assert card.hp == 120
    assert card.energy_type == EnergyType.LIGHTNING
    assert len(card.attacks) == 2

    prompt = PokemonCardPromptBuilder.build_prompt(card)
    assert "Pikachu Special" in prompt
    assert "120 HP" in prompt
    assert "Electro Ball" in prompt
    assert "Thunderbolt" in prompt
    assert "Gill Sans" in prompt
    assert "63.5 x 88.9 mm" in prompt
    print("[OK] Teste de Schema e Prompt Builder passou com sucesso!")


def test_txt_format_parsing():
    sample_txt = """
    name: Charizard Custom
    hp: 180
    type: Fire
    stage: Stage 2
    evolves_from: Charmeleon
    attack: Fire: Flamethrower: 120: Discard an Energy card.
    retreat: 2
    illustrator: Victor Rubinec
    style: classic
    """
    card = PokemonCardData._from_text_kv(sample_txt, fallback_name="charizard")
    assert card.name == "Charizard Custom"
    assert card.hp == 180
    assert card.energy_type == EnergyType.FIRE
    assert card.stage.value == "Stage 2"
    assert card.evolves_from == "Charmeleon"
    assert card.style == CardStyle.CLASSIC
    assert len(card.attacks) == 1
    assert card.attacks[0].name == "Flamethrower"
    assert card.attacks[0].damage == "120"

    prompt = PokemonCardPromptBuilder.build_prompt(card)
    assert "Charizard Custom" in prompt
    assert "Flamethrower" in prompt
    assert "CLASSIC RETRO ERA" in prompt
    print("[OK] Teste de parsing TXT/chave-valor passou com sucesso!")


def test_product_profile_integration():
    profile = PRODUCT_REGISTRY[ProductType.POKEMON_CARD]
    json_path = Path("data/input/pokemon_card/exemplo_pikachu.json")
    
    # Simula imagem com o mesmo nome
    fake_img = json_path.parent / "exemplo_pikachu.png"
    fake_img.touch()
    try:
        prompt = profile.get_prompt_for_image(fake_img)
        assert "Pikachu Special" in prompt
        assert "120 HP" in prompt
        print("[OK] Teste de integracao do Perfil ProductProfile passou com sucesso!")
    finally:
        if fake_img.exists():
            fake_img.unlink()


if __name__ == "__main__":
    test_schema_and_prompt()
    test_txt_format_parsing()
    test_product_profile_integration()
    print("\n[SUCESSO] Todos os testes de validacao do modulo Pokemon passaram!")
