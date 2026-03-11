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

BOOK_CHAPTER_COUNTS = {
    "Genesis": 50,
    "Exodus": 40,
    "Leviticus": 27,
    "Numbers": 36,
    "Deuteronomy": 34,
    "Joshua": 24,
    "Judges": 21,
    "Ruth": 4,
    "1 Samuel": 31,
    "2 Samuel": 24,
    "1 Kings": 22,
    "2 Kings": 25,
    "1 Chronicles": 29,
    "2 Chronicles": 36,
    "Ezra": 10,
    "Nehemiah": 13,
    "Esther": 10,
    "Job": 42,
    "Psalms": 150,
    "Proverbs": 31,
    "Ecclesiastes": 12,
    "Song of Solomon": 8,
    "Isaiah": 66,
    "Jeremiah": 52,
    "Lamentations": 5,
    "Ezekiel": 48,
    "Daniel": 12,
    "Hosea": 14,
    "Joel": 3,
    "Amos": 9,
    "Obadiah": 1,
    "Jonah": 4,
    "Micah": 7,
    "Nahum": 3,
    "Habakkuk": 3,
    "Zephaniah": 3,
    "Haggai": 2,
    "Zechariah": 14,
    "Malachi": 4,
    "Matthew": 28,
    "Mark": 16,
    "Luke": 24,
    "John": 21,
    "Acts": 28,
    "Romans": 16,
    "1 Corinthians": 16,
    "2 Corinthians": 13,
    "Galatians": 6,
    "Ephesians": 6,
    "Philippians": 4,
    "Colossians": 4,
    "1 Thessalonians": 5,
    "2 Thessalonians": 3,
    "1 Timothy": 6,
    "2 Timothy": 4,
    "Titus": 3,
    "Philemon": 1,
    "Hebrews": 13,
    "James": 5,
    "1 Peter": 5,
    "2 Peter": 3,
    "1 John": 5,
    "2 John": 1,
    "3 John": 1,
    "Jude": 1,
    "Revelation": 22,
}


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


def _pick_random_chapter() -> tuple[str, int]:
    book = random.choice(list(BOOK_CHAPTER_COUNTS.keys()))
    chapter = random.randint(1, BOOK_CHAPTER_COUNTS[book])
    return book, chapter


def _get_random_online_verse(bible_api_base: str, attempts: int = 10) -> tuple[str, str]:
    base = bible_api_base.rstrip("/")

    for _ in range(attempts):
        book, chapter = _pick_random_chapter()
        chapter_ref = f"{book} {chapter}"

        response = requests.get(f"{base}/{chapter_ref}", timeout=15)
        response.raise_for_status()
        payload = response.json()

        verses = payload.get("verses") if isinstance(payload, dict) else None
        if isinstance(verses, list) and verses:
            candidates = []
            for verse in verses:
                if not isinstance(verse, dict):
                    continue
                verse_num = verse.get("verse")
                verse_text = str(verse.get("text", "")).strip()
                if verse_text and verse_num is not None:
                    reference = f"{book} {chapter}:{verse_num}"
                    candidates.append((" ".join(verse_text.split()), reference))

            if candidates:
                return random.choice(candidates)

        fallback_text = str(payload.get("text", "")).strip() if isinstance(payload, dict) else ""
        if fallback_text:
            return " ".join(fallback_text.split()), str(payload.get("reference", chapter_ref)).strip()

    raise RuntimeError("Could not fetch a random online verse from chapter pool.")


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
        try:
            verse_text, reference = _get_random_online_verse(bible_api_base=bible_api_base, attempts=10)
            if verse_text and reference:
                return verse_text, reference, "online"
        except Exception:
            fallback_reference = random.choice(DEFAULT_REFERENCES)
            try:
                response = requests.get(
                    f"{bible_api_base.rstrip('/')}/{fallback_reference}",
                    timeout=15,
                )
                response.raise_for_status()
                payload = response.json()
                verse_text = str(payload.get("text", "")).strip()
                if verse_text:
                    return " ".join(verse_text.split()), fallback_reference, "online"
            except Exception:
                if normalized == "online":
                    raise

    local_verses = _get_local_verses(local_path)
    if local_verses:
        verse = random.choice(local_verses)
        return verse["text"], verse["reference"], "local"

    raise RuntimeError("Could not fetch a verse from online API or local JSON.")
