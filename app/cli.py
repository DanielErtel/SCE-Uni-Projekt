"""CLI - Kommandozeilen-Interface fuer das SCE Uni Projekt."""

import sys
from pathlib import Path

import click

from app import __version__
from app.config import get_all_extensions, OUTPUT_DIR


@click.group()
@click.version_option(version=__version__)
def cli():
    """SCE Uni Projekt - Universelles Content-Analyse-Tool.

    Verarbeitet Websites, PDFs, Word, Excel, PowerPoint, Bilder und Videos.
    Speichert alles in einer durchsuchbaren Wissensdatenbank.
    """
    pass


# ─── EINLESEN ────────────────────────────────────────────────────────

@cli.command()
@click.argument("pfad", type=click.Path(exists=True))
@click.option("--rekursiv", "-r", is_flag=True, help="Unterordner einbeziehen")
def einlesen(pfad, rekursiv):
    """Datei oder Ordner einlesen und in Wissensdatenbank speichern.

    Beispiele:
        python run.py einlesen dokument.pdf
        python run.py einlesen ./ordner -r
    """
    from app.parsers.router import parse_file, detect_type
    from app.storage.database import get_db, add_source, add_content

    path = Path(pfad)
    conn = get_db()

    if path.is_file():
        _process_file(conn, path)
    elif path.is_dir():
        extensions = get_all_extensions()
        pattern = "**/*" if rekursiv else "*"
        files = [f for f in path.glob(pattern) if f.suffix.lower() in extensions]

        if not files:
            click.echo(f"Keine unterstuetzten Dateien in {path} gefunden.")
            return

        click.echo(f"{len(files)} Dateien gefunden.")
        with click.progressbar(files, label="Verarbeite") as bar:
            for f in bar:
                _process_file(conn, f)
    else:
        click.echo(f"Pfad nicht gefunden: {pfad}", err=True)
        sys.exit(1)

    conn.close()
    click.echo("Fertig!")


def _process_file(conn, file_path: Path):
    """Einzelne Datei verarbeiten und speichern."""
    from app.parsers.router import parse_file

    try:
        results = parse_file(file_path)
        if not results:
            click.echo(f"  Kein Inhalt: {file_path.name}")
            return

        source_id = _register_source(conn, file_path)

        from app.storage.database import add_content
        for item in results:
            add_content(
                conn, source_id,
                content_type=item.get("content_type", "text"),
                content=item["text"],
                page_number=item.get("page"),
                section=item.get("section"),
                metadata={k: v for k, v in item.items()
                          if k not in ("text", "content_type", "page", "section")},
            )

        click.echo(f"  OK: {file_path.name} ({len(results)} Abschnitte)")

    except Exception as e:
        click.echo(f"  FEHLER: {file_path.name} - {e}", err=True)


def _register_source(conn, file_path: Path) -> int:
    """Quelle in der Datenbank registrieren."""
    from app.storage.database import add_source
    return add_source(
        conn,
        source_type="file",
        source_path=str(file_path.resolve()),
        file_type=file_path.suffix.lower().lstrip("."),
        file_size=file_path.stat().st_size,
    )


# ─── CRAWLEN ─────────────────────────────────────────────────────────

@cli.command()
@click.argument("url")
@click.option("--follow", "-f", is_flag=True, help="Links auf gleicher Domain folgen")
@click.option("--max-seiten", "-m", type=int, default=10, help="Max. Seiten bei --follow")
def crawlen(url, follow, max_seiten):
    """Website crawlen und Inhalt extrahieren.

    Beispiele:
        python run.py crawlen https://example.com
        python run.py crawlen https://example.com --follow --max-seiten 20
    """
    from app.crawlers.web import crawl_url
    from app.storage.database import get_db, add_source, add_content

    click.echo(f"Crawle {url}...")
    results = crawl_url(url, follow_links=follow, max_pages=max_seiten)

    if not results:
        click.echo("Keine Inhalte gefunden.")
        return

    conn = get_db()
    for page in results:
        source_id = add_source(
            conn,
            source_type="url",
            source_path=page["url"],
            file_type="url",
            metadata={"status_code": page["status_code"]},
        )
        for item in page["content"]:
            add_content(
                conn, source_id,
                content_type=item.get("content_type", "text"),
                content=item["text"],
                section=item.get("section"),
            )

    conn.close()
    click.echo(f"{len(results)} Seite(n) verarbeitet und gespeichert.")


# ─── SUCHE ───────────────────────────────────────────────────────────

@cli.command()
@click.argument("suchbegriff")
@click.option("--limit", "-l", type=int, default=10, help="Max. Ergebnisse")
def suche(suchbegriff, limit):
    """Wissensdatenbank durchsuchen.

    Beispiele:
        python run.py suche "maschinelles lernen"
        python run.py suche "KI Strategie" --limit 20
    """
    from app.storage.database import get_db, search

    conn = get_db()
    results = search(conn, suchbegriff, limit=limit)
    conn.close()

    if not results:
        click.echo("Keine Ergebnisse.")
        return

    click.echo(f"\n{len(results)} Ergebnis(se):\n")
    for i, r in enumerate(results, 1):
        click.echo(f"  {i}. [{r['source_path']}]")
        snippet = r["snippet"].replace(">>>", "\033[1m").replace("<<<", "\033[0m")
        click.echo(f"     {snippet}\n")


# ─── KI-ANALYSE ──────────────────────────────────────────────────────

@cli.command()
@click.argument("pfad", type=click.Path(exists=True))
@click.option("--aktion", "-a",
              type=click.Choice(["zusammenfassung", "extraktion", "frage", "custom"]),
              default="zusammenfassung", help="Art der Analyse")
@click.option("--prompt", "-p", default="", help="Eigener Prompt (fuer 'frage' oder 'custom')")
@click.option("--speichern", "-s", is_flag=True, help="Ergebnis in DB speichern")
def analyse(pfad, aktion, prompt, speichern):
    """Datei per KI analysieren.

    Beispiele:
        python run.py analyse dokument.pdf
        python run.py analyse bericht.docx -a frage -p "Was sind die Hauptergebnisse?"
        python run.py analyse tabelle.xlsx -a extraktion -p "Alle Firmennamen"
    """
    from app.parsers.router import parse_file
    from app.ai import analyzer
    from app.storage.database import get_db, add_analysis

    path = Path(pfad)
    click.echo(f"Lese {path.name}...")

    # Datei parsen
    results = parse_file(path)
    text = "\n\n".join(r["text"] for r in results)

    if not text.strip():
        click.echo("Kein Text zum Analysieren gefunden.")
        return

    # Text kuerzen falls zu lang
    if len(text) > 100000:
        click.echo(f"Text gekuerzt (von {len(text)} auf 100.000 Zeichen)")
        text = text[:100000]

    click.echo(f"Analysiere ({aktion})...")

    if aktion == "zusammenfassung":
        result = analyzer.summarize(text)
    elif aktion == "extraktion":
        result = analyzer.extract_data(text, prompt or "Alle wichtigen Informationen")
    elif aktion == "frage":
        if not prompt:
            click.echo("Bitte Frage mit --prompt angeben.", err=True)
            sys.exit(1)
        result = analyzer.ask(text, prompt)
    elif aktion == "custom":
        if not prompt:
            click.echo("Bitte Prompt mit --prompt angeben.", err=True)
            sys.exit(1)
        result = analyzer.analyze_custom(text, prompt)

    click.echo(f"\n{'─' * 60}")
    click.echo(result)
    click.echo(f"{'─' * 60}")

    # In DB speichern
    if speichern:
        conn = get_db()
        source_id = _register_source(conn, path)
        add_analysis(
            conn, source_id,
            analysis_type=aktion,
            result=result,
            prompt=prompt,
        )
        conn.close()
        click.echo("\nErgebnis gespeichert.")


# ─── STATUS ──────────────────────────────────────────────────────────

@cli.command()
def status():
    """Statistiken der Wissensdatenbank anzeigen."""
    from app.storage.database import get_db, get_stats

    conn = get_db()
    stats = get_stats(conn)
    conn.close()

    click.echo(f"\n{'═' * 40}")
    click.echo("  WISSENSDATENBANK")
    click.echo(f"{'═' * 40}")
    click.echo(f"  Quellen:   {stats['quellen']}")
    click.echo(f"  Inhalte:   {stats['inhalte']}")
    click.echo(f"  Analysen:  {stats['analysen']}")

    if stats["typen"]:
        click.echo(f"\n  Nach Typ:")
        for typ, count in sorted(stats["typen"].items()):
            click.echo(f"    {typ or 'unbekannt':12s} {count}")

    click.echo(f"{'═' * 40}\n")


# ─── QUELLEN ─────────────────────────────────────────────────────────

@cli.command()
@click.option("--typ", "-t", type=click.Choice(["file", "url", "fileshare"]),
              help="Nach Typ filtern")
def quellen(typ):
    """Alle gespeicherten Quellen auflisten."""
    from app.storage.database import get_db, get_sources

    conn = get_db()
    sources = get_sources(conn, source_type=typ)
    conn.close()

    if not sources:
        click.echo("Keine Quellen gespeichert.")
        return

    click.echo(f"\n{len(sources)} Quelle(n):\n")
    for s in sources:
        size = ""
        if s.get("file_size"):
            size_kb = s["file_size"] / 1024
            size = f" ({size_kb:.0f} KB)"
        click.echo(f"  [{s['id']}] {s['source_type']:5s} | {s['file_type'] or '?':5s} | "
                    f"{s['source_path']}{size}")


if __name__ == "__main__":
    cli()
