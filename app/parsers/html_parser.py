"""HTML-Dateien und Webseiten-Content parsen."""

from pathlib import Path
from bs4 import BeautifulSoup


def parse_html(file_path: Path) -> list[dict]:
    """Lokale HTML-Datei einlesen."""
    for encoding in ["utf-8", "latin-1", "cp1252"]:
        try:
            text = file_path.read_text(encoding=encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        return [{"text": "[HTML nicht lesbar - Encoding-Problem]", "content_type": "text"}]

    return parse_html_content(text)


def parse_html_content(html: str) -> list[dict]:
    """HTML-String zu strukturiertem Text parsen."""
    soup = BeautifulSoup(html, "html.parser")

    # Script/Style entfernen
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    results = []

    # Titel
    title = soup.find("title")
    if title and title.text.strip():
        results.append({
            "text": title.text.strip(),
            "content_type": "text",
            "section": "Titel",
        })

    # Meta-Beschreibung
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc and meta_desc.get("content"):
        results.append({
            "text": meta_desc["content"],
            "content_type": "text",
            "section": "Meta-Beschreibung",
        })

    # Haupttext nach Abschnitten
    for heading in soup.find_all(["h1", "h2", "h3", "h4"]):
        section_text = []
        section_title = heading.get_text(strip=True)

        # Text bis zur naechsten Ueberschrift sammeln
        for sibling in heading.find_next_siblings():
            if sibling.name and sibling.name.startswith("h"):
                break
            text = sibling.get_text(strip=True)
            if text:
                section_text.append(text)

        if section_text:
            results.append({
                "text": "\n".join(section_text),
                "content_type": "text",
                "section": section_title,
            })

    # Falls keine Ueberschriften: gesamten Text nehmen
    if not results or len(results) <= 2:
        full_text = soup.get_text(separator="\n", strip=True)
        # Leere Zeilen reduzieren
        lines = [l for l in full_text.split("\n") if l.strip()]
        if lines:
            results.append({
                "text": "\n".join(lines),
                "content_type": "text",
                "section": "Volltext",
            })

    # Tabellen
    for table_idx, table in enumerate(soup.find_all("table")):
        rows = []
        for tr in table.find_all("tr"):
            cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
            if any(cells):
                rows.append(cells)
        if rows:
            text_lines = [" | ".join(row) for row in rows]
            results.append({
                "text": "\n".join(text_lines),
                "content_type": "table",
                "section": f"Tabelle {table_idx + 1}",
            })

    # Links sammeln
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        if href.startswith("http") and text:
            links.append(f"{text}: {href}")

    if links:
        results.append({
            "text": "\n".join(links[:50]),  # Max 50 Links
            "content_type": "text",
            "section": "Links",
        })

    return results
