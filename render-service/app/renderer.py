import math
import random
import re
import struct
import subprocess
import textwrap
import unicodedata
import wave
from pathlib import Path


MUSIC_EXTENSIONS = {".mp3", ".wav", ".aac", ".m4a", ".flac", ".ogg"}


def sanitize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    normalized = normalized.replace("\r", " ").replace("□", " ")
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    cleaned = "".join(ch if 32 <= ord(ch) <= 126 else " " for ch in ascii_text)
    return " ".join(cleaned.split())


def safe_output_name(name: str) -> str:
    base = Path(name).name
    stem = re.sub(r"[^a-zA-Z0-9._-]", "_", base)
    if not stem.lower().endswith(".mp4"):
        stem += ".mp4"
    return stem


def wrap_for_mobile(text: str) -> list[str]:
    return textwrap.wrap(text, width=18) or [text]


def estimate_verse_font_size(lines: list[str]) -> int:
    longest = max((len(line) for line in lines), default=1)
    safe_width = 1080 * 0.84
    approx = int(safe_width / max(1.0, longest * 0.58))
    return max(34, min(54, approx))


def escape_filter_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\\\'")


def escape_drawtext_text(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("'", "\\\\'")
        .replace(":", "\\:")
        .replace("%", "\\%")
        .replace("\n", "\\n")
    )


def generate_fallback_music(destination: Path, duration: float, sample_rate: int = 44100) -> None:
    total_samples = int(duration * sample_rate)
    with wave.open(str(destination), "wb") as wav_file:
        wav_file.setnchannels(2)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)

        for i in range(total_samples):
            t = i / sample_rate
            beat_pos = (t * 84.0 / 60.0) % 1.0
            env = max(0.0, 1.0 - beat_pos * 5.5) if beat_pos < 0.18 else 0.0
            kick = math.sin(2.0 * math.pi * 48.0 * t) * env
            pad = math.sin(2.0 * math.pi * 220.0 * t) * 0.12
            sample = max(-1.0, min(1.0, kick * 0.85 + pad * 0.35))
            pcm = int(sample * 32767)
            wav_file.writeframesraw(struct.pack("<hh", pcm, pcm))


def pick_music_file(music_dir: Path, requested_music_file: str | None) -> Path | None:
    if requested_music_file:
        candidate = music_dir / Path(requested_music_file).name
        if candidate.exists() and candidate.is_file():
            return candidate

    files = [
        path
        for path in music_dir.iterdir()
        if path.is_file() and path.suffix.lower() in MUSIC_EXTENSIONS
    ]
    if not files:
        return None
    return random.choice(files)


def build_filter_complex(
    verse_lines: list[str],
    reference: str,
    duration: float,
    verse_font_size: int,
    reference_font_size: int,
) -> str:
    fade_alpha = "if(lt(t\\,1)\\,t\\,1)"
    audio_fade_out_start = max(0.0, duration - 1.0)
    font_file = escape_filter_value("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf")

    line_gap = 8
    line_height = verse_font_size + line_gap
    total_block_height = len(verse_lines) * line_height
    start_y = int(0.43 * 1920 - (total_block_height / 2))

    video_parts = [
        f"[0:v]format=yuv420p,trim=duration={duration},setpts=PTS-STARTPTS",
    ]

    for i, line in enumerate(verse_lines):
        escaped_line = escape_drawtext_text(line)
        y = start_y + (i * line_height)
        video_parts.append(
            "drawtext="
            f"fontfile='{font_file}':"
            f"text='{escaped_line}':"
            "expansion=none:text_shaping=0:"
            f"fontcolor=white:fontsize={verse_font_size}:"
            "x=(w-text_w)/2:"
            f"y={y}:"
            "shadowcolor=black@0.0:shadowx=0:shadowy=0:borderw=0:"
            f"alpha='{fade_alpha}'"
        )

    escaped_reference = escape_drawtext_text(reference)
    video_parts.append(
        "drawtext="
        f"fontfile='{font_file}':"
        f"text='{escaped_reference}':"
        "expansion=none:text_shaping=0:"
        f"fontcolor=white:fontsize={reference_font_size}:"
        "x=(w-text_w)/2:y=(h*0.72):"
        "shadowcolor=black@0.0:shadowx=0:shadowy=0:borderw=0:"
        f"alpha='{fade_alpha}'"
    )

    video_chain = ",".join(video_parts) + "[v]"
    audio_chain = (
        "[1:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,"
        "volume=1.4,"
        "acompressor=threshold=-24dB:ratio=2.5:attack=120:release=900:makeup=6,"
        "alimiter=limit=0.96,"
        "afade=t=in:st=0:d=1,"
        f"afade=t=out:st={audio_fade_out_start}:d=1[a]"
    )
    return f"{video_chain};{audio_chain}"


def render_short(
    ffmpeg_binary: str,
    output_dir: Path,
    tmp_dir: Path,
    music_dir: Path,
    verse: str,
    reference: str,
    duration: float,
    requested_music_file: str | None,
    output_name: str,
) -> tuple[Path, str, str | None]:
    output_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    cleaned_verse = sanitize_text(verse)
    cleaned_reference = sanitize_text(reference)

    verse_lines = wrap_for_mobile(cleaned_verse)
    verse_font_size = estimate_verse_font_size(verse_lines)
    reference_font_size = max(28, verse_font_size - 10)

    output_file = output_dir / safe_output_name(output_name)

    selected_music = pick_music_file(music_dir, requested_music_file)
    fallback_music = tmp_dir / "_fallback_music.wav"

    if selected_music is None:
        generate_fallback_music(fallback_music, duration)
        audio_input = fallback_music
        audio_name = None
    else:
        audio_input = selected_music
        audio_name = selected_music.name

    filter_complex = build_filter_complex(
        verse_lines=verse_lines,
        reference=cleaned_reference,
        duration=duration,
        verse_font_size=verse_font_size,
        reference_font_size=reference_font_size,
    )

    command = [
        ffmpeg_binary,
        "-y",
        "-f",
        "lavfi",
        "-i",
        "color=c=black:s=1080x1920:r=30",
        "-stream_loop",
        "-1",
        "-i",
        str(audio_input),
        "-filter_complex",
        filter_complex,
        "-map",
        "[v]",
        "-map",
        "[a]",
        "-t",
        str(duration),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-ar",
        "44100",
        str(output_file),
    ]

    result = subprocess.run(command, capture_output=True, text=True)
    logs = (result.stdout or "") + "\n" + (result.stderr or "")
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed with code {result.returncode}:\n{logs[-6000:]}")

    if fallback_music.exists():
        fallback_music.unlink()

    return output_file, logs[-6000:], audio_name
