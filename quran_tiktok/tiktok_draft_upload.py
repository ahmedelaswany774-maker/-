#!/usr/bin/env python3
"""Upload a generated MP4 to TikTok as a draft after OAuth authorization.

This does not publish publicly. TikTok requires the user to review and finish
posting in the TikTok app for the documented inbox upload flow.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import secrets
import sys
import webbrowser
from pathlib import Path
from urllib.parse import urlencode, urlparse, parse_qs

import requests

AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
INIT_URL = "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/"
STATUS_URL = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"
REDIRECT_URI = os.getenv("TIKTOK_REDIRECT_URI", "https://localhost:8080/callback")
SCOPES = "user.info.basic,video.upload"


def make_pkce() -> tuple[str, str]:
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


def auth(args: argparse.Namespace) -> dict:
    if not args.client_key or not args.client_secret:
        raise SystemExit("Set TIKTOK_CLIENT_KEY and TIKTOK_CLIENT_SECRET first.")
    verifier, challenge = make_pkce()
    state = secrets.token_urlsafe(24)
    params = {
        "client_key": args.client_key,
        "response_type": "code",
        "scope": SCOPES,
        "redirect_uri": args.redirect_uri,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    url = AUTH_URL + "?" + urlencode(params)
    print("Open this URL in the TikTok account browser and approve access:\n")
    print(url)
    try:
        webbrowser.open(url)
    except Exception:
        pass
    callback = input("Paste the full callback URL (or only the code): ").strip()
    if callback.startswith("http"):
        query = parse_qs(urlparse(callback).query)
        returned_state = query.get("state", [""])[0]
        if returned_state != state:
            raise SystemExit("OAuth state mismatch; restart authentication.")
        code = query.get("code", [""])[0]
    else:
        code = callback
    if not code:
        raise SystemExit("No authorization code received.")
    response = requests.post(TOKEN_URL, data={
        "client_key": args.client_key,
        "client_secret": args.client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": args.redirect_uri,
        "code_verifier": verifier,
    }, timeout=30)
    response.raise_for_status()
    token = response.json()
    Path(args.token_file).write_text(json.dumps(token, indent=2), encoding="utf-8")
    print(f"Saved token to {args.token_file}")
    return token


def load_token(args: argparse.Namespace) -> dict:
    path = Path(args.token_file)
    if not path.exists():
        return auth(args)
    return json.loads(path.read_text(encoding="utf-8"))


def upload_draft(args: argparse.Namespace) -> None:
    path = Path(args.video).resolve()
    if not path.exists():
        raise SystemExit(f"Video not found: {path}")
    token = load_token(args)
    size = path.stat().st_size
    headers = {"Authorization": f"Bearer {token['access_token']}", "Content-Type": "application/json"}
    response = requests.post(INIT_URL, headers=headers, json={
        "source_info": {"source": "FILE_UPLOAD", "video_size": size, "chunk_size": size, "total_chunk_count": 1}
    }, timeout=30)
    response.raise_for_status()
    data = response.json()["data"]
    upload_url = data["upload_url"]
    publish_id = data["publish_id"]
    with path.open("rb") as video_file:
        put_response = requests.put(upload_url, headers={
            "Content-Range": f"bytes 0-{size - 1}/{size}",
            "Content-Type": "video/mp4",
        }, data=video_file, timeout=120)
    put_response.raise_for_status()
    print(json.dumps({"publish_id": publish_id, "status": "uploaded_as_draft"}, indent=2))
    print("Open TikTok notifications to review and finish the post.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload a Quran MP4 to TikTok as a draft.")
    parser.add_argument("video", nargs="?", help="Path to MP4")
    parser.add_argument("--oauth-only", action="store_true", help="Run OAuth and save tokens without uploading a video.")
    parser.add_argument("--token-file", default="tiktok_token.json")
    parser.add_argument("--client-key", default=os.getenv("TIKTOK_CLIENT_KEY"))
    parser.add_argument("--client-secret", default=os.getenv("TIKTOK_CLIENT_SECRET"))
    parser.add_argument("--redirect-uri", default=REDIRECT_URI)
    args = parser.parse_args()
    try:
        if args.oauth_only:
            auth(args)
        else:
            if not args.video:
                parser.error("video is required unless --oauth-only is used")
            upload_draft(args)
    except requests.HTTPError as exc:
        print(f"TikTok API error: {exc.response.text}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
