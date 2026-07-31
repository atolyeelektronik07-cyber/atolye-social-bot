"""Instagram Graph API ile içerik paylaşımı.

Instagram iki adımlı çalışır:
  1. Medya konteyneri oluştur (görselin herkese açık bir URL'de olması şart)
  2. Konteyneri yayınla

Video/Reels için konteynerin işlenmesi zaman aldığından durum sorgulanır.
"""

from __future__ import annotations

import time

import requests

from . import config


class InstagramError(RuntimeError):
    pass


def _post(path: str, params: dict) -> dict:
    params = {**params, "access_token": config.META_TOKEN}
    response = requests.post(f"{config.GRAPH_BASE}/{path}", data=params, timeout=120)
    payload = response.json()
    if "error" in payload:
        raise InstagramError(payload["error"].get("message", str(payload["error"])))
    return payload


def _get(path: str, params: dict) -> dict:
    params = {**params, "access_token": config.META_TOKEN}
    response = requests.get(f"{config.GRAPH_BASE}/{path}", params=params, timeout=60)
    payload = response.json()
    if "error" in payload:
        raise InstagramError(payload["error"].get("message", str(payload["error"])))
    return payload


def _wait_until_ready(creation_id: str, timeout_seconds: int = 300) -> None:
    """Video konteyneri hazır olana kadar bekler."""
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        status = _get(creation_id, {"fields": "status_code,status"})
        code = status.get("status_code")
        if code == "FINISHED":
            return
        if code == "ERROR":
            raise InstagramError(f"Medya işlenemedi: {status.get('status')}")
        time.sleep(5)
    raise InstagramError("Medya işleme zaman aşımına uğradı.")


def publish(caption: str, media_path: str | None, is_video: bool = False) -> str:
    if not config.IG_USER_ID:
        raise InstagramError("IG_USER_ID tanımlı değil.")
    if not media_path:
        raise InstagramError(
            "Instagram sadece görsel/video ile paylaşıma izin veriyor; "
            "post dosyasına 'media:' satırı ekle."
        )

    url = config.media_url(media_path)

    if config.DRY_RUN:
        print(f"  [DRY RUN] Instagram → {url}")
        return "dry-run"

    if is_video:
        container = _post(
            f"{config.IG_USER_ID}/media",
            {"media_type": "REELS", "video_url": url, "caption": caption},
        )
        creation_id = container["id"]
        _wait_until_ready(creation_id)
    else:
        container = _post(
            f"{config.IG_USER_ID}/media",
            {"image_url": url, "caption": caption},
        )
        creation_id = container["id"]

    published = _post(
        f"{config.IG_USER_ID}/media_publish", {"creation_id": creation_id}
    )
    return published["id"]
