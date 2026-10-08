"""Limpeza das pastas data/input e/ou data/output.

Preserva a estrutura de pastas por produto, os arquivos .gitkeep e os guias .md.

Exemplos:
    python clean.py --target output
    python clean.py --target input --dry-run
    python clean.py --target all --yes
    python clean.py -t output -p pdf_extract
"""
import argparse
import shutil
import sys
from pathlib import Path
from typing import List

DATA_DIR = Path(__file__).resolve().parent / "data"
PRESERVED_NAMES = {".gitkeep"}
PRESERVED_SUFFIXES = {".md"}


def is_preserved(path: Path) -> bool:
    return path.is_file() and (path.name in PRESERVED_NAMES or path.suffix.lower() in PRESERVED_SUFFIXES)


def collect_items(root: Path, product: str = None) -> List[Path]:
    """Lista itens de primeiro nível a remover dentro de cada pasta de produto de `root`."""
    items: List[Path] = []
    if not root.exists():
        return items
    for product_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        if product and product_dir.name.lower() != product.lower():
            continue
        for item in sorted(product_dir.iterdir()):
            if not is_preserved(item):
                items.append(item)
    # arquivos soltos na raiz (fora de pastas de produto)
    if not product:
        items.extend(sorted(f for f in root.iterdir() if f.is_file() and not is_preserved(f)))
    return items


def remove(item: Path) -> None:
    if item.is_dir():
        shutil.rmtree(item)
    else:
        item.unlink()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Limpa as pastas data/input e/ou data/output.")
    parser.add_argument("--target", "-t", choices=["input", "output", "all"], required=True,
                        help="O que limpar: input, output ou all (ambos)")
    parser.add_argument("--product", "-p", default=None,
                        help="Limita a uma pasta de produto (ex: poster_a4, pdf_extract)")
    parser.add_argument("--dry-run", "-n", action="store_true",
                        help="Apenas lista o que seria removido")
    parser.add_argument("--yes", "-y", action="store_true",
                        help="Não pede confirmação")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    targets = ["input", "output"] if args.target == "all" else [args.target]

    items: List[Path] = []
    for t in targets:
        items.extend(collect_items(DATA_DIR / t, args.product))

    if not items:
        print("Nada para limpar.")
        return

    print(f"Itens a remover ({', '.join(targets)}):")
    for item in items:
        print(f"  - {item.relative_to(DATA_DIR.parent)}{'/' if item.is_dir() else ''}")

    if args.dry_run:
        print(f"\n[dry-run] {len(items)} item(ns) seriam removidos.")
        return

    if not args.yes:
        answer = input(f"\nRemover {len(items)} item(ns) permanentemente? [s/N] ").strip().lower()
        if answer not in ("s", "sim", "y", "yes"):
            print("Cancelado.")
            return

    failed = 0
    for item in items:
        try:
            remove(item)
        except Exception as e:
            failed += 1
            print(f"❌ Falha ao remover {item}: {e}")
    print(f"\n🧹 {len(items) - failed} item(ns) removidos, {failed} falha(s).")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
