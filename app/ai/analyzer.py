"""KI-Analyse mit Claude API."""

import anthropic

from app.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL


def get_client() -> anthropic.Anthropic:
    """Anthropic-Client erstellen."""
    if not ANTHROPIC_API_KEY:
        raise ValueError(
            "ANTHROPIC_API_KEY nicht gesetzt. "
            "Bitte in .env eintragen oder als Umgebungsvariable setzen."
        )
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def summarize(text: str, context: str = "") -> str:
    """Text zusammenfassen."""
    client = get_client()
    prompt = "Erstelle eine ausfuehrliche Zusammenfassung des folgenden Texts auf Deutsch."
    if context:
        prompt += f"\n\nKontext: {context}"
    prompt += f"\n\nText:\n{text}"

    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def extract_data(text: str, instruction: str) -> str:
    """Strukturierte Daten aus Text extrahieren."""
    client = get_client()
    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": (
            f"Extrahiere die folgenden Informationen aus dem Text:\n"
            f"{instruction}\n\n"
            f"Antworte strukturiert (JSON oder Tabelle).\n\n"
            f"Text:\n{text}"
        )}],
    )
    return response.content[0].text


def ask(text: str, question: str) -> str:
    """Frage zu einem Text beantworten."""
    client = get_client()
    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": (
            f"Beantworte die folgende Frage basierend auf dem gegebenen Text.\n"
            f"Antworte auf Deutsch.\n\n"
            f"Frage: {question}\n\n"
            f"Text:\n{text}"
        )}],
    )
    return response.content[0].text


def analyze_custom(text: str, prompt: str) -> str:
    """Eigene KI-Analyse mit benutzerdefiniertem Prompt."""
    client = get_client()
    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": f"{prompt}\n\nText:\n{text}"}],
    )
    return response.content[0].text
