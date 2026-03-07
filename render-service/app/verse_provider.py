import json
import random
from pathlib import Path

import requests


DEFAULT_REFERENCES = [
    "Psalm 46:10",
    "Psalm 23:1",
    "Matthew 11:28",
    "Psalm 34:18",
    "Isaiah 41:10",
    "2 Corinthians 12:9",
    "Psalm 46:1",
    "Philippians 4:13",
    "John 1:5",
    "1 Peter 5:7",
    "Isaiah 40:29",
    "Romans 8:31",
    "Psalm 119:105",
    "Exodus 14:14",
    "1 Corinthians 16:14",
    "Matthew 5:8",
    "Psalm 51:10",
    "2 Corinthians 5:7",
    "Lamentations 3:22",
    "John 14:27",
]


def _get_local_verses(local_path: Path) -> list[dict[str, str]]:
    if not local_path.exists():
        return []

    with local_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        return []

    cleaned: list[dict[str, str]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text", "")).strip()
        reference = str(item.get("reference", "")).strip()
        if text and reference:
            cleaned.append({"text": text, "reference": reference})

    return cleaned


def get_random_verse(source: str, bible_api_base: str, local_path: Path) -> tuple[str, str, str]:
    normalized = source.lower().strip()

    if normalized in {"local", "auto"}:
        local_verses = _get_local_verses(local_path)
        if normalized == "local" and not local_verses:
            raise RuntimeError("Local verse source selected but no verses found in local file.")
        if local_verses and normalized == "local":
            verse = random.choice(local_verses)
            return verse["text"], verse["reference"], "local"

    if normalized in {"online", "auto"}:
        reference = random.choice(DEFAULT_REFERENCES)
        try:
            response = requests.get(
                f"{bible_api_base.rstrip('/')}/{reference}",
                timeout=15,
            )
            response.raise_for_status()
            payload = response.json()
            verse_text = str(payload.get("text", "")).strip()
            if verse_text:
                return " ".join(verse_text.split()), reference, "online"
        except Exception:
            if normalized == "online":
                raise

    local_verses = _get_local_verses(local_path)
    if local_verses:
        verse = random.choice(local_verses)
        return verse["text"], verse["reference"], "local"

    raise RuntimeError("Could not fetch a verse from online API or local JSON.")
