# Quran TikTok Channel

This directory contains the automated Quran short-video pipeline. It selects non-repeating ayahs, fetches Arabic text, English translation, and Mishari Alafasy recitation, then renders vertical 1080x1920 MP4 videos.

Start with:

```bash
cd quran_tiktok
python3 -m pip install -r requirements.txt
python3 run_channel.py
```

Generated files are written to `quran_tiktok/output/ready_to_post/` and are ignored by Git. TikTok draft upload requires a TikTok Developer app and user OAuth; credentials are never committed.
