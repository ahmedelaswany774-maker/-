#!/usr/bin/env python3
"""Generate vertical Quran TikTok videos from non-repeating random ayahs.

The generator creates local MP4 files only. It does not publish automatically.
It stores used ayah keys in state.json and marks an ayah used only after
successful video creation.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from arabic_reshaper import reshape
from bidi.algorithm import get_display

API_BASE = "https://api.alquran.cloud/v1"
AUDIO_BASE = "https://verses.quran.foundation/Alafasy/mp3"
WIDTH, HEIGHT = 1080, 1920
TIMEOUT = 30

# Quran.com uses this reciter as Mishari Rashid al-`Afasy. The public audio
# endpoint uses the canonical Alafasy slug.
RECITER = "Mishari Rashid al-`Afasy"
TRANSLATION = "Saheeh International / English"


def get_json(url: str) -> dict[str, Any]:
    response = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": "quran-tiktok-generator/1.0"})
    response.raise_for_status()
    payload = response.json()
    if payload.get("code") not in (None, 200):
        raise RuntimeError(f"Quran API error from {url}: {payload}")
    return payload


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"used": [], "generated": []}
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def load_chapters() -> list[dict[str, Any]]:
    data = get_json(f"{API_BASE}/surah")["data"]
    return [{"number": int(x["number"]), "name": x["englishName"], "arabic": x["name"], "ayahs": int(x["numberOfAyahs"])} for x in data]


def all_ayahs(chapters: list[dict[str, Any]]) -> list[tuple[int, int, int]]:
    rows: list[tuple[int, int, int]] = []
    global_number = 1
    for chapter in chapters:
        for ayah in range(1, chapter["ayahs"] + 1):
            rows.append((chapter["number"], ayah, global_number))
            global_number += 1
    return rows


def choose_ayah(rows: list[tuple[int, int, int]], used: set[str], rng: random.Random) -> tuple[int, int, int]:
    available = [row for row in rows if f"{row[0]}:{row[1]}" not in used]
    if not available:
        raise RuntimeError("All 6236 ayahs have already been used. Remove state.json to restart.")
    return rng.choice(available)


def fetch_ayah(surah: int, ayah: int) -> tuple[str, str]:
    # Separate requests make the edition names explicit and easier to replace.
    arabic = get_json(f"{API_BASE}/ayah/{surah}:{ayah}/quran-uthmani")["data"]["text"]
    english = get_json(f"{API_BASE}/ayah/{surah}:{ayah}/en.sahih")["data"]["text"]
    return arabic.strip(), english.strip()


def download_audio(surah: int, ayah: int, destination: Path) -> None:
    url = f"{AUDIO_BASE}/{surah:03d}{ayah:03d}.mp3"
    response = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": "quran-tiktok-generator/1.0"})
    response.raise_for_status()
    destination.write_bytes(response.content)


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    found = shutil.which("fc-match")
    if found:
        result = subprocess.run([found, "-f", "%{file}", name], capture_output=True, text=True, check=True)
        if result.stdout and Path(result.stdout).exists():
            return ImageFont.truetype(result.stdout, size)
    candidates = [
        "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def arabic_visual(text: str) -> str:
    return get_display(reshape(text))


def wrap_text(draw: ImageDraw.ImageDraw, text: str, selected_font: ImageFont.FreeTypeFont, max_width: int, rtl: bool = False) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if rtl:
            box = draw.textbbox((0, 0), candidate, font=selected_font, direction="rtl")
            measured = box[2] - box[0]
        else:
            measured = draw.textbbox((0, 0), candidate, font=selected_font)[2]
        if measured <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_centered_block(draw: ImageDraw.ImageDraw, lines: list[str], y: int, selected_font: ImageFont.FreeTypeFont, fill: tuple[int, int, int, int], spacing: int = 18, rtl: bool = False) -> int:
    heights = []
    for line in lines:
        box = draw.textbbox((0, 0), line, font=selected_font, direction="rtl" if rtl else None)
        heights.append(box[3] - box[1])
    total = sum(heights) + spacing * max(0, len(lines) - 1)
    cursor = y
    for line, height in zip(lines, heights):
        direction = "rtl" if rtl else None
        if rtl:
            draw.text((WIDTH // 2 + 3, cursor + 3), line, anchor="ma", direction=direction, font=selected_font, fill=(0, 0, 0, 150))
            draw.text((WIDTH // 2, cursor), line, anchor="ma", direction=direction, font=selected_font, fill=fill)
        else:
            box = draw.textbbox((0, 0), line, font=selected_font)
            x = (WIDTH - (box[2] - box[0])) // 2
            draw.text((x + 3, cursor + 3), line, font=selected_font, fill=(0, 0, 0, 150))
            draw.text((x, cursor), line, font=selected_font, fill=fill)
        cursor += height + spacing
    return total


def fit_text(draw: ImageDraw.ImageDraw, text: str, family: str, start_size: int, min_size: int, max_width: int, max_height: int, spacing: int, rtl: bool = False) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    for size in range(start_size, min_size - 1, -2):
        selected_font = font(family, size)
        visual = text
        lines = wrap_text(draw, visual, selected_font, max_width, rtl=rtl)
        heights = [draw.textbbox((0, 0), line, font=selected_font)[3] for line in lines]
        total = sum(heights) + spacing * max(0, len(lines) - 1)
        if total <= max_height:
            return selected_font, lines
    selected_font = font(family, min_size)
    visual = text
    return selected_font, wrap_text(draw, visual, selected_font, max_width, rtl=rtl)


def create_frame(path: Path, chapter: dict[str, Any], surah: int, ayah: int, arabic: str, english: str, handle: str) -> None:
    background = Image.new("RGBA", (WIDTH, HEIGHT), (8, 18, 38, 255))
    pixels = background.load()
    for y in range(HEIGHT):
        ratio = y / HEIGHT
        color = (10 + int(18 * ratio), 25 + int(22 * ratio), 48 + int(36 * ratio), 255)
        for x in range(WIDTH):
            pixels[x, y] = color
    background = background.filter(ImageFilter.GaussianBlur(0.4))
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rounded_rectangle((55, 205, WIDTH - 55, HEIGHT - 210), radius=48, fill=(0, 0, 0, 120), outline=(198, 166, 88, 170), width=3)

    title_font = font("Noto Sans Arabic", 40)
    english_title_font = font("Noto Sans", 30)
    footer_font = font("Noto Sans", 28)
    arabic_font, arabic_lines = fit_text(draw, arabic, "Noto Sans Arabic", 82, 50, WIDTH - 190, 560, 18, rtl=True)
    english_font, english_lines = fit_text(draw, english, "Noto Sans", 44, 28, WIDTH - 210, 360, 12, rtl=False)

    draw.text((WIDTH // 2, 285), chapter['arabic'], anchor="ma", direction="rtl", font=title_font, fill=(246, 224, 166, 255))
    subtitle = f"{chapter['name']}  •  Surah {surah}"
    subtitle_box = draw.textbbox((0, 0), subtitle, font=english_title_font)
    draw.text(((WIDTH - (subtitle_box[2] - subtitle_box[0])) // 2, 345), subtitle, font=english_title_font, fill=(210, 220, 236, 245))

    arabic_height = draw_centered_block(draw, arabic_lines, 525, arabic_font, (255, 255, 255, 255), spacing=18, rtl=True)
    divider_y = min(1160, 525 + arabic_height + 55)
    draw.line((170, divider_y, WIDTH - 170, divider_y), fill=(198, 166, 88, 170), width=2)
    english_y = divider_y + 42
    english_height = draw_centered_block(draw, english_lines, english_y, english_font, (225, 235, 246, 255), spacing=12)

    footer = f"Quran {surah}:{ayah}  •  {RECITER}"
    footer_box = draw.textbbox((0, 0), footer, font=footer_font)
    footer_y = HEIGHT - 420
    draw.text(((WIDTH - (footer_box[2] - footer_box[0])) // 2, footer_y), footer, font=footer_font, fill=(205, 214, 228, 235))
    watermark = handle
    watermark_box = draw.textbbox((0, 0), watermark, font=footer_font)
    draw.text(((WIDTH - (watermark_box[2] - watermark_box[0])) // 2, footer_y + 55), watermark, font=footer_font, fill=(198, 166, 88, 235))

    background.alpha_composite(overlay)
    background.convert("RGB").save(path, quality=95)

def render_video(frame: Path, audio: Path, output: Path) -> None:
    command = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-loop", "1", "-i", str(frame), "-i", str(audio),
        "-c:v", "libx264", "-preset", "medium", "-tune", "stillimage",
        "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p",
        "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
        "-shortest", "-movflags", "+faststart", str(output),
    ]
    subprocess.run(command, check=True)


def safe_slug(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", text).strip("_")


def generate_one(chapters: list[dict[str, Any]], rows: list[tuple[int, int, int]], state: dict[str, Any], root: Path, rng: random.Random, handle: str) -> Path:
    used = set(state.get("used", []))
    surah, ayah, global_ayah = choose_ayah(rows, used, rng)
    chapter = chapters[surah - 1]
    key = f"{surah}:{ayah}"
    work = root / "work"
    output_dir = root / "ready_to_post"
    work.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{surah:03d}_{ayah:03d}_{safe_slug(chapter['name'])}"
    frame = work / f"{stem}.jpg"
    audio = work / f"{stem}.mp3"
    output = output_dir / f"{stem}.mp4"
    metadata = output_dir / f"{stem}.json"

    print(f"Generating {key} — {chapter['name']} — global ayah {global_ayah}")
    arabic, english = fetch_ayah(surah, ayah)
    download_audio(surah, ayah, audio)
    create_frame(frame, chapter, surah, ayah, arabic, english, handle)
    render_video(frame, audio, output)
    metadata.write_text(json.dumps({
        "ayah_key": key,
        "surah": surah,
        "surah_name": chapter["name"],
        "surah_name_ar": chapter["arabic"],
        "ayah": ayah,
        "global_ayah": global_ayah,
        "reciter": RECITER,
        "translation": TRANSLATION,
        "caption": f"{chapter['name']} {surah}:{ayah} | Mishari Alafasy\\n#quran #islam #fyp #quranrecitation",
        "sources": {
            "text": f"{API_BASE}/ayah/{surah}:{ayah}/quran-uthmani",
            "translation": f"{API_BASE}/ayah/{surah}:{ayah}/en.sahih",
            "audio": f"{AUDIO_BASE}/{surah:03d}{ayah:03d}.mp3",
        },
        "created_at": int(time.time()),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    state.setdefault("used", []).append(key)
    state.setdefault("generated", []).append({"ayah_key": key, "file": str(output), "created_at": int(time.time())})
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate non-repeating Quran TikTok videos.")
    parser.add_argument("--count", type=int, default=1, help="Number of videos to generate")
    parser.add_argument("--output", default="quran_tiktok_output", help="Output directory")
    parser.add_argument("--seed", type=int, default=None, help="Optional random seed for reproducible selection")
    parser.add_argument("--state", default=None, help="Optional path to state JSON")
    parser.add_argument("--handle", default="@quran_daily_reflection", help="TikTok handle shown as watermark")
    args = parser.parse_args()
    if args.count < 1:
        parser.error("--count must be at least 1")

    root = Path(args.output).resolve()
    root.mkdir(parents=True, exist_ok=True)
    state_path = Path(args.state).resolve() if args.state else root / "state.json"
    state = load_state(state_path)
    rng = random.Random(args.seed)

    try:
        chapters = load_chapters()
        rows = all_ayahs(chapters)
        if len(rows) != 6236:
            raise RuntimeError(f"Expected 6236 ayahs, received {len(rows)}")
        for _ in range(args.count):
            output = generate_one(chapters, rows, state, root, rng, args.handle)
            save_state(state_path, state)
            print(f"Created: {output}")
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Done. Generated {args.count} video(s). Used ayahs: {len(state.get('used', []))}/6236")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
