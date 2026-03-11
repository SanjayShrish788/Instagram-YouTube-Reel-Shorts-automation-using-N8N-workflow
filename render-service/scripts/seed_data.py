import json
import math
import struct
import wave
from pathlib import Path

from app.config import settings


SAMPLE_VERSES = [
    {
        "text": "Be still, and know that I am God.",
        "reference": "Psalm 46:10",
    },
    {
        "text": "God is our refuge and strength, an ever-present help in trouble.",
        "reference": "Psalm 46:1",
    },
    {
        "text": "The Lord is close to the brokenhearted and saves those who are crushed in spirit.",
        "reference": "Psalm 34:18",
    },
]


def write_sample_verses(path: Path) -> None:
    if path.exists():
        return
    path.write_text(json.dumps(SAMPLE_VERSES, indent=2), encoding="utf-8")


def write_sample_music(path: Path) -> None:
    if path.exists():
        return

    sample_rate = 44100
    duration = 10.0
    total_samples = int(sample_rate * duration)

    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(2)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)

        for i in range(total_samples):
            t = i / sample_rate
            pulse = math.sin(2 * math.pi * 50 * t) * max(0.0, 1.0 - ((t * 80 / 60) % 1.0) * 5)
            pad = math.sin(2 * math.pi * 180 * t) * 0.1
            sample = max(-1.0, min(1.0, pulse * 0.8 + pad))
            pcm = int(sample * 32767)
            wav_file.writeframesraw(struct.pack("<hh", pcm, pcm))


def main() -> None:
    settings.music_dir.mkdir(parents=True, exist_ok=True)
    settings.local_verses_path.parent.mkdir(parents=True, exist_ok=True)

    write_sample_verses(settings.local_verses_path)

    print("Seed complete.")


if __name__ == "__main__":
    main()
