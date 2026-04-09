"""Zentrale Konfiguration."""

import os
from pathlib import Path
from dotenv import load_dotenv

# .env laden
load_dotenv()

# Pfade
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
INPUT_DIR = DATA_DIR / "input"
OUTPUT_DIR = DATA_DIR / "output"
DB_PATH = DATA_DIR / "knowledge.db"

# KI
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

# Web-Crawling
CRAWL_TIMEOUT = int(os.getenv("CRAWL_TIMEOUT", "30"))
CRAWL_MAX_PAGES = int(os.getenv("CRAWL_MAX_PAGES", "50"))
USER_AGENT = "SCE-Uni-Projekt/0.1 (Content-Analyse)"

# Verarbeitung
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "100"))
SUPPORTED_EXTENSIONS = {
    "dokumente": [".pdf", ".docx", ".doc", ".txt", ".md", ".rtf"],
    "tabellen": [".xlsx", ".xls", ".csv"],
    "praesentation": [".pptx", ".ppt"],
    "bilder": [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff"],
    "video": [".mp4", ".avi", ".mov", ".mkv", ".webm"],
    "web": [".html", ".htm"],
}


def get_all_extensions() -> list[str]:
    """Alle unterstuetzten Dateiendungen."""
    exts = []
    for group in SUPPORTED_EXTENSIONS.values():
        exts.extend(group)
    return exts
