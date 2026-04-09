"""CEO-Briefing-Agent — Erzeugt ueberzeugende, logisch stichhaltige Nachrichten.

Nutzt bewiesene Frameworks:
- Minto Pyramid Principle (McKinsey)
- SCQA/SCR-Framework
- BLUF (Bottom Line Up Front)
- Cialdinis 7 Prinzipien der Ueberzeugung
- Steel-Man-Technik
- Verlustaversion / Cost of Inaction
- Toulmin-Argumentationsmodell
"""

import json
from pathlib import Path

import anthropic

from app.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL, DATA_DIR


SYSTEM_PROMPT = """Du bist ein hochprofessioneller Executive-Communication-Spezialist.
Deine Aufgabe: Nachrichten fuer den CEO aufbereiten, die ueberzeugend, logisch stichhaltig und
strategisch formuliert sind — sodass die vertretene Position als offensichtlich richtige Wahl erscheint.

## FRAMEWORKS DIE DU ANWENDEST

### 1. BLUF (Bottom Line Up Front)
- Empfehlung/Kernbotschaft im ERSTEN Satz
- Dann Dringlichkeit, dann Fakten, dann CTA

### 2. Minto Pyramid Principle
- Von oben nach unten: Schlussfolgerung → stuetzende Argumente → Daten
- MECE-strukturiert (keine Ueberlappung, vollstaendig abgedeckt)

### 3. SCQA-Framework
- Situation (unbestreitbarer Kontext)
- Complication (Problem/Veraenderung)
- Question (implizite Frage)
- Answer (deine Empfehlung)

### 4. Ueberzeugungstechniken
- Verlustaversion: "Was wir VERLIEREN wenn wir nicht handeln" > "Was wir gewinnen"
- Steel-Man: Das staerkste Gegenargument selbst formulieren und entkraeften
- Praemissenkette: Durch zustimmungspflichtige Aussagen fuehren
- Social Proof: Vergleichbare Unternehmen/Referenzen nennen
- Konsistenz: An fruehere CEO-Aussagen ankoppeln
- Knappheit: Zeitfenster und Deadlines betonen
- Drei-Optionen-Technik: Empfehlung als mittlere Option

### 5. Sprache
- Direkt, nicht devot ("Ich empfehle" statt "Vielleicht koennten wir")
- Strategisch, nicht operativ (Business Impact statt technische Details)
- Quantifiziert (EUR, %, Stunden, Monate — nie vage)
- Aktiv, kurze Saetze (max 20 Woerter)
- Selbstsicher mit Integritaet

### 6. Struktur
- Max 1 Seite Kernbotschaft
- Klarer Call to Action mit Deadline
- Maximal 3 Kernargumente
- Proaktiv mindestens 1 Gegenargument entkraeften

## REGELN
- NIEMALS devote Formulierungen ("vielleicht", "eventuell", "es waere schoen")
- IMMER quantifizieren — keine vagen Aussagen
- IMMER einen konkreten Call to Action mit Deadline
- IMMER mindestens ein Gegenargument proaktiv entkraeften (Steel-Man)
- Sprache: Deutsch, professionell, C-Level-angemessen
- Der CEO ist der Held der Geschichte — nicht die Loesung
- KEINE Eigenannahmen — nur verifizierte Fakten verwenden
"""


def load_knowledge_base() -> str:
    """Alle gesammelten Quelleninformationen laden."""
    knowledge_parts = []

    # Quellenanalyse laden
    quellenanalyse = DATA_DIR / "output" / "quellenanalyse.md"
    if quellenanalyse.exists():
        knowledge_parts.append(quellenanalyse.read_text(encoding="utf-8"))

    # Weitere Analysedateien im output-Ordner
    output_dir = DATA_DIR / "output"
    if output_dir.exists():
        for f in sorted(output_dir.glob("*.md")):
            if f.name != "quellenanalyse.md" and f.name != "CEO_Briefing_Kompendium.md":
                try:
                    knowledge_parts.append(f.read_text(encoding="utf-8"))
                except Exception:
                    pass

    # Datenbank-Inhalte laden
    try:
        from app.storage.database import get_db, search, get_sources
        conn = get_db()
        sources = get_sources(conn)
        if sources:
            knowledge_parts.append("\n## Gespeicherte Quellen in der Wissensdatenbank:")
            for s in sources:
                knowledge_parts.append(f"- [{s['file_type']}] {s['source_path']}")
        conn.close()
    except Exception:
        pass

    return "\n\n---\n\n".join(knowledge_parts) if knowledge_parts else ""


def generate_briefing(
    thema: str,
    position: str,
    kontext: str = "",
    ceo_name: str = "",
    format_typ: str = "memo",
    zusatz_fakten: str = "",
) -> str:
    """CEO-Briefing generieren.

    Args:
        thema: Worum geht es? (z.B. "SCE Friends & Fellows Mitgliedschaft")
        position: Welche Meinung vertrittst du? (z.B. "Silber-Mitgliedschaft abschliessen")
        kontext: Zusaetzlicher Kontext (z.B. "Wir waren bei einem SCE-Event")
        ceo_name: Name des CEOs (optional)
        format_typ: 'memo', 'email', 'pitch' (60-Sekunden-Script)
        zusatz_fakten: Weitere Fakten die einbezogen werden sollen

    Returns:
        Fertiges CEO-Briefing als String
    """
    if not ANTHROPIC_API_KEY:
        raise ValueError(
            "ANTHROPIC_API_KEY nicht gesetzt. "
            "Bitte in .env eintragen oder als Umgebungsvariable setzen."
        )

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # Wissensbasis laden
    knowledge = load_knowledge_base()

    # Format-spezifische Anweisungen
    format_instructions = _get_format_instructions(format_typ)

    # User-Prompt zusammenbauen
    user_prompt = f"""## AUFGABE
Erstelle ein CEO-Briefing zum folgenden Thema.

## THEMA
{thema}

## MEINE POSITION (die ueberzeugend vertreten werden soll)
{position}

## ZUSAETZLICHER KONTEXT
{kontext if kontext else "Kein zusaetzlicher Kontext."}

{f"## CEO-NAME: {ceo_name}" if ceo_name else ""}

## FORMAT
{format_instructions}

## ZUSAETZLICHE FAKTEN
{zusatz_fakten if zusatz_fakten else "Keine zusaetzlichen Fakten."}

## WISSENSBASIS (nutze diese Informationen als Grundlage)
{knowledge if knowledge else "Keine Wissensbasis verfuegbar — arbeite mit den gegebenen Informationen."}

## WICHTIG
- Schreibe so, dass meine Position als die offensichtlich logische und stichhaltige Wahl erscheint
- Nutze Verlustaversion: Was VERLIEREN wir wenn wir nicht handeln?
- Baue eine Praemissenkette auf, der der CEO bei jedem Schritt zustimmen muss
- Entkraefte proaktiv das staerkste Gegenargument (Steel-Man)
- Quantifiziere wo moeglich
- Schlage einen konkreten naechsten Schritt mit Deadline vor
- KEINE spekulativen Zahlen — nur belegbare Fakten oder kennzeichne Schaetzungen explizit
"""

    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=8192,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    return response.content[0].text


def _get_format_instructions(format_typ: str) -> str:
    """Format-spezifische Anweisungen zurueckgeben."""
    formats = {
        "memo": """Erstelle ein ENTSCHEIDUNGSMEMO (max. 1 Seite):
1. EMPFEHLUNG (1-2 Saetze, fett)
2. DRINGLICHKEIT (1 Satz)
3. KONTEXT (2-3 Saetze)
4. ENTSCHEIDUNGSGRUNDLAGE (3-5 Bullet Points mit Fakten)
5. OPTIONEN (3 Optionen, Empfehlung hervorgehoben)
6. RISIKEN & MITIGATION (2-3 Punkte)
7. BENOETIGTE ENTSCHEIDUNG (CTA mit Deadline)""",

        "email": """Erstelle eine CEO-E-MAIL im SCQA+BLUF-Format:
- Betreff: [ENTSCHEIDUNG NOETIG] Thema bis Datum
- BLUF: Empfehlung in 1-2 Saetzen
- Hintergrund (Situation, 1 Satz)
- Das Problem (Complication, 1-2 Saetze)
- 3 stuetzende Fakten
- Staerkstes Gegenargument + Widerlegung
- Naechster Schritt (CTA + Deadline)""",

        "pitch": """Erstelle ein 60-SEKUNDEN ELEVATOR-PITCH-SCRIPT:
- [10 Sek] HOOK: Konkreter Verlust/Problem
- [15 Sek] KONTEXT: Was der Pilot/die Daten zeigen
- [15 Sek] EMPFEHLUNG: Konkrete Massnahme + ROI
- [10 Sek] GEGENARGUMENT: Staerkstes Gegenargument + Widerlegung
- [10 Sek] CTA: Was du brauchst + Deadline""",

        "argumentation": """Erstelle eine VOLLSTAENDIGE ARGUMENTATIONSKETTE:
1. Praemissen die der CEO akzeptieren MUSS (3-5 Stueck)
2. Faktengrundlage (quantifiziert)
3. Logische Schlussfolgerung (unvermeidlich)
4. Steel-Man: Staerkstes Gegenargument + Entkraeftung
5. Inokulierung: Gegen welche kuenftigen Einwaende "impfen"
6. Cost of Inaction: Was Nichtstun kostet
7. Call to Action mit Deadline""",
    }

    return formats.get(format_typ, formats["memo"])


def interactive_briefing() -> str:
    """Interaktiver Modus — fragt alle Informationen ab."""
    import click

    click.echo("\n" + "=" * 60)
    click.echo("  CEO-BRIEFING GENERATOR")
    click.echo("=" * 60 + "\n")

    thema = click.prompt("Thema (worum geht es?)")
    position = click.prompt("Deine Position (was willst du erreichen?)")
    kontext = click.prompt("Zusaetzlicher Kontext", default="", show_default=False)
    ceo_name = click.prompt("CEO-Name", default="", show_default=False)

    format_typ = click.prompt(
        "Format",
        type=click.Choice(["memo", "email", "pitch", "argumentation"]),
        default="memo",
    )

    zusatz = click.prompt("Weitere Fakten/Argumente", default="", show_default=False)

    click.echo("\nGeneriere Briefing...")

    result = generate_briefing(
        thema=thema,
        position=position,
        kontext=kontext,
        ceo_name=ceo_name,
        format_typ=format_typ,
        zusatz_fakten=zusatz,
    )

    return result
