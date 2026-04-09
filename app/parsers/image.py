"""Bilder analysieren - OCR und KI-Beschreibung."""

import base64
from pathlib import Path

from app.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL


def parse_image(file_path: Path) -> list[dict]:
    """Bild einlesen und per KI beschreiben lassen."""
    results = []

    # OCR mit Tesseract (falls verfuegbar)
    ocr_text = _try_ocr(file_path)
    if ocr_text:
        results.append({
            "text": ocr_text,
            "content_type": "text",
            "section": "OCR-Text",
        })

    # KI-Bildbeschreibung (falls API-Key vorhanden)
    if ANTHROPIC_API_KEY:
        description = _describe_with_ai(file_path)
        if description:
            results.append({
                "text": description,
                "content_type": "image_desc",
                "section": "KI-Bildbeschreibung",
            })

    if not results:
        results.append({
            "text": f"[Bild: {file_path.name} - keine Analyse moeglich (kein OCR/API-Key)]",
            "content_type": "image_ref",
        })

    return results


def _try_ocr(file_path: Path) -> str:
    """OCR mit Tesseract versuchen."""
    try:
        from PIL import Image
        import pytesseract
        img = Image.open(str(file_path))
        text = pytesseract.image_to_string(img, lang="deu+eng").strip()
        return text if len(text) > 10 else ""
    except Exception:
        return ""


def _describe_with_ai(file_path: Path) -> str:
    """Bild per Claude Vision beschreiben."""
    try:
        import anthropic

        suffix = file_path.suffix.lower()
        media_types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        media_type = media_types.get(suffix, "image/png")

        with open(file_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": "Beschreibe dieses Bild ausfuehrlich auf Deutsch. "
                                "Was ist zu sehen? Welche Texte/Zahlen sind erkennbar?",
                    },
                ],
            }],
        )
        return response.content[0].text
    except Exception as e:
        return f"[Bildbeschreibung fehlgeschlagen: {e}]"


def image_to_base64(file_path: Path) -> str:
    """Bild als Base64-String fuer API-Aufrufe."""
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")
