"""Zentraler Parser-Router - erkennt Dateityp und leitet an richtigen Parser."""

from pathlib import Path

from app.config import SUPPORTED_EXTENSIONS


def parse_file(file_path: Path) -> list[dict]:
    """Datei automatisch erkennen und parsen.

    Args:
        file_path: Pfad zur Datei

    Returns:
        Liste von Content-Dicts mit 'text', 'content_type', etc.

    Raises:
        ValueError: Wenn Dateityp nicht unterstuetzt
        FileNotFoundError: Wenn Datei nicht existiert
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Datei nicht gefunden: {file_path}")

    suffix = file_path.suffix.lower()

    # PDF
    if suffix in SUPPORTED_EXTENSIONS["dokumente"] and suffix == ".pdf":
        from app.parsers.pdf import parse_pdf
        return parse_pdf(file_path)

    # Word
    if suffix in (".docx", ".doc"):
        from app.parsers.word import parse_word
        return parse_word(file_path)

    # Excel / CSV
    if suffix in SUPPORTED_EXTENSIONS["tabellen"]:
        from app.parsers.excel import parse_excel
        return parse_excel(file_path)

    # PowerPoint
    if suffix in SUPPORTED_EXTENSIONS["praesentation"]:
        from app.parsers.powerpoint import parse_powerpoint
        return parse_powerpoint(file_path)

    # Bilder
    if suffix in SUPPORTED_EXTENSIONS["bilder"]:
        from app.parsers.image import parse_image
        return parse_image(file_path)

    # Video
    if suffix in SUPPORTED_EXTENSIONS["video"]:
        from app.parsers.video import parse_video
        return parse_video(file_path)

    # HTML
    if suffix in SUPPORTED_EXTENSIONS["web"]:
        from app.parsers.html_parser import parse_html
        return parse_html(file_path)

    # Plaintext (.txt, .md, .rtf)
    if suffix in (".txt", ".md", ".rtf"):
        return _parse_text(file_path)

    raise ValueError(
        f"Dateityp '{suffix}' wird nicht unterstuetzt.\n"
        f"Unterstuetzte Typen: {_list_supported()}"
    )


def _parse_text(file_path: Path) -> list[dict]:
    """Einfache Textdateien einlesen."""
    for encoding in ["utf-8", "latin-1", "cp1252"]:
        try:
            text = file_path.read_text(encoding=encoding)
            return [{
                "text": text,
                "content_type": "text",
                "section": "Volltext",
            }]
        except UnicodeDecodeError:
            continue
    return [{"text": "[Nicht lesbar - Encoding-Problem]", "content_type": "text"}]


def _list_supported() -> str:
    """Alle unterstuetzten Typen als String."""
    parts = []
    for category, exts in SUPPORTED_EXTENSIONS.items():
        parts.append(f"  {category}: {', '.join(exts)}")
    return "\n".join(parts)


def detect_type(file_path: Path) -> str | None:
    """Dateityp-Kategorie erkennen."""
    suffix = file_path.suffix.lower()
    for category, exts in SUPPORTED_EXTENSIONS.items():
        if suffix in exts:
            return category
    return None
