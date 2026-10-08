"""Extração de páginas de PDF como imagens (uma imagem por página inteira)."""
from pathlib import Path
from typing import List, Optional, Set


def parse_page_ranges(spec: Optional[str], total_pages: int) -> List[int]:
    """Converte '1-3,5' em índices base-0 [0, 1, 2, 4]. None retorna todas as páginas."""
    if not spec:
        return list(range(total_pages))
    pages: Set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_s, end_s = part.split("-", 1)
            start, end = int(start_s), int(end_s)
        else:
            start = end = int(part)
        for n in range(start, end + 1):
            if 1 <= n <= total_pages:
                pages.add(n - 1)
    return sorted(pages)


class PdfPageExtractor:
    """Renderiza cada página de um PDF em PNG com o DPI desejado."""

    @staticmethod
    def extract(
        pdf_path: Path,
        output_dir: Path,
        dpi: int = 300,
        pages: Optional[str] = None,
        force: bool = False,
        logger=None,
    ) -> List[Path]:
        import pymupdf as fitz

        pdf_path = Path(pdf_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        doc = fitz.open(str(pdf_path))
        try:
            if doc.needs_pass:
                raise ValueError(f"PDF protegido por senha: {pdf_path.name}")

            total = doc.page_count
            indices = parse_page_ranges(pages, total)
            width = max(3, len(str(total)))
            zoom = dpi / 72.0
            matrix = fitz.Matrix(zoom, zoom)

            results: List[Path] = []
            for idx in indices:
                out_path = output_dir / f"{pdf_path.stem}_p{idx + 1:0{width}d}.png"
                if out_path.exists() and out_path.stat().st_size > 0 and not force:
                    if logger:
                        logger.info(f"⏭️  Página {idx + 1}/{total} já extraída: {out_path.name}")
                    results.append(out_path)
                    continue

                pix = doc[idx].get_pixmap(matrix=matrix, alpha=False)
                pix.set_dpi(dpi, dpi)
                pix.save(str(out_path))
                if logger:
                    logger.info(f"✅ Página {idx + 1}/{total} -> {out_path.name} ({pix.width}x{pix.height}px)")
                results.append(out_path)
            return results
        finally:
            doc.close()
