#!/usr/bin/env python3
"""Run the channel generator from channel_config.json."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "channel_config.json"
OUTPUT = ROOT / "output"


def main() -> int:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    count = int(config.get("daily_count", 1))
    handle = str(config.get("handle", "@noor_ayah_daily"))
    command = [
        sys.executable,
        str(ROOT / "generate_quran_tiktok.py"),
        "--count", str(count),
        "--output", str(OUTPUT),
        "--handle", handle,
    ]
    completed = subprocess.run(command, cwd=ROOT)
    if completed.returncode != 0:
        return completed.returncode

    hashtags = " ".join(config.get("hashtags", []))
    ar_template = config.get("caption_template_ar", "{surah_name_ar}، الآية {surah}:{ayah}")
    en_template = config.get("caption_template_en", "{surah_name}, verse {surah}:{ayah}")
    for metadata_path in sorted((OUTPUT / "ready_to_post").glob("*.json")):
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        values = {
            "surah": metadata["surah"],
            "ayah": metadata["ayah"],
            "surah_name": metadata["surah_name"],
            "surah_name_ar": metadata["surah_name_ar"],
        }
        metadata["channel_name_ar"] = config.get("channel_name_ar", "نور الآية")
        metadata["channel_name_en"] = config.get("channel_name_en", "Noor Ayah")
        metadata["caption"] = f"{ar_template.format(**values)}\n{en_template.format(**values)}\n{hashtags}".strip()
        metadata["review_before_posting"] = bool(config.get("review_before_posting", True))
        metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
