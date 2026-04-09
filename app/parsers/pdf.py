"""PDF-Dateien einlesen und Text extrahieren."""

from pathlib import Path
import fitz  # PyMuPDF


def parse_pdf(file_path: Path) -> list[dict]:
    """PDF einlesen. Gibt Liste von Seiten mit Text zurueck."""
    doc = fitz.open(str(file_path))
    pages = []

    for page_num, page in enumerate(doc, 1):
        text = page.get_text("text").strip()
        if text:
            pages.append({
                "page": page_num,
                "text": text,
                "content_type": "text",
            })

        # Bilder auf der Seite erkennen
        images = page.get_images(full=True)
        if images:
            pages.append({
                "page": page_num,
                "text": f"[{len(images)} Bild(er) auf Seite {page_num}]",
                "content_type": "image_ref",
                "image_count": len(images),
            })

    doc.close()
    return pages


def extract_pdf_images(file_path: Path, output_dir: Path) -> list[Path]:
    """Bilder aus PDF extrahieren und speichern."""
    doc = fitz.open(str(file_path))
    output_dir.mkdir(parents=True, exist_ok=True)
    saved = []

    for page_num, page in enumerate(doc, 1):
        for img_idx, img in enumerate(page.get_images(full=True)):
            xref = img[0]
            pix = fitz.Pixmap(doc, xref)
            if pix.n - pix.alpha > 3:  # CMYK
                pix = fitz.Pixmap(fitz.csRGB, pix)
            out_path = output_dir / f"page{page_num}_img{img_idx + 1}.png"
            pix.save(str(out_path))
            saved.append(out_path)

    doc.close()
    return saved
