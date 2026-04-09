"""Website-Crawler - Seiten einlesen und Links folgen."""

import time
from urllib.parse import urljoin, urlparse
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from app.config import CRAWL_TIMEOUT, CRAWL_MAX_PAGES, USER_AGENT
from app.parsers.html_parser import parse_html_content


def crawl_url(url: str, follow_links: bool = False,
              max_pages: int = None) -> list[dict]:
    """Eine URL crawlen und Inhalt extrahieren.

    Args:
        url: Zu crawlende URL
        follow_links: Auch verlinkten Seiten folgen?
        max_pages: Max. Anzahl Seiten (Standard: config)

    Returns:
        Liste von Seiten mit extrahiertem Content
    """
    max_pages = max_pages or CRAWL_MAX_PAGES
    visited = set()
    to_visit = [url]
    results = []
    base_domain = urlparse(url).netloc

    while to_visit and len(visited) < max_pages:
        current_url = to_visit.pop(0)

        if current_url in visited:
            continue

        page_data = _fetch_page(current_url)
        if not page_data:
            continue

        visited.add(current_url)

        # Content parsen
        parsed = parse_html_content(page_data["html"])
        results.append({
            "url": current_url,
            "status_code": page_data["status_code"],
            "content": parsed,
        })

        # Links folgen (nur auf gleicher Domain)
        if follow_links:
            soup = BeautifulSoup(page_data["html"], "html.parser")
            for a in soup.find_all("a", href=True):
                link = urljoin(current_url, a["href"])
                parsed_link = urlparse(link)
                # Nur gleiche Domain, kein Fragment, kein Query
                if (parsed_link.netloc == base_domain
                        and link not in visited
                        and not parsed_link.fragment
                        and parsed_link.scheme in ("http", "https")):
                    clean_link = f"{parsed_link.scheme}://{parsed_link.netloc}{parsed_link.path}"
                    if clean_link not in visited:
                        to_visit.append(clean_link)

        # Hoeflichkeitspause
        if follow_links:
            time.sleep(1)

    return results


def _fetch_page(url: str) -> dict | None:
    """Einzelne Seite laden."""
    try:
        response = requests.get(
            url,
            timeout=CRAWL_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
        )
        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if "text/html" not in content_type and "text/plain" not in content_type:
            return None

        return {
            "html": response.text,
            "status_code": response.status_code,
        }
    except requests.RequestException as e:
        print(f"  Fehler bei {url}: {e}")
        return None


def download_file(url: str, output_dir: Path) -> Path | None:
    """Datei von URL herunterladen."""
    try:
        response = requests.get(
            url,
            timeout=CRAWL_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
            stream=True,
        )
        response.raise_for_status()

        # Dateiname aus URL oder Content-Disposition
        filename = Path(urlparse(url).path).name or "download"
        output_path = output_dir / filename
        output_dir.mkdir(parents=True, exist_ok=True)

        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        return output_path
    except requests.RequestException as e:
        print(f"  Download fehlgeschlagen: {e}")
        return None
