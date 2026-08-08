import argparse
import json
import os
import re
import shutil
import sys
import time
import urllib.request
from datetime import datetime, timedelta

if sys.stdout is not None:
    sys.stdout.reconfigure(encoding="utf-8")

API_URL = "https://app-api6.podbbang.com/channels/{channel_id}/episodes"
HEADERS = {"User-Agent": "Mozilla/5.0"}


def safe_filename(name: str) -> str:
    return re.sub(r'[\/:*?"<>|]', "_", name).strip()


def fetch_episodes_page(channel_id: str, offset: int, limit: int = 20) -> dict:
    url = (
        f"{API_URL.format(channel_id=channel_id)}"
        f"?offset={offset}&limit={limit}&sort=desc&episode_id=0&focus_center=0&with=image"
    )
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.load(resp)


def download_file(url: str, dest_path: str, progress_callback=None):
    if os.path.exists(dest_path):
        print(f"  이미 존재함, 건너뜀: {os.path.basename(dest_path)}")
        return
    tmp_path = dest_path + ".part"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60) as resp:
        total = resp.length or int(resp.headers.get("Content-Length", 0) or 0)
        downloaded = 0
        with open(tmp_path, "wb") as f:
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if progress_callback is not None:
                    percent = (downloaded / total * 100) if total else 0.0
                    progress_callback(percent, downloaded, total)
    os.replace(tmp_path, dest_path)
    if progress_callback is not None:
        progress_callback(100.0, downloaded, downloaded)
    print(f"  다운로드 완료: {os.path.basename(dest_path)}")


def download_recent_episodes(channel_id: str, days: int, output_dir: str, progress_callback=None):
    os.makedirs(output_dir, exist_ok=True)
    cutoff = datetime.now() - timedelta(days=days)

    offset = 0
    downloaded = 0
    while True:
        page = fetch_episodes_page(channel_id, offset)
        items = page.get("data", [])
        if not items:
            break

        stop = False
        for ep in items:
            published = datetime.strptime(ep["publishedAt"], "%Y-%m-%d %H:%M:%S")
            if published < cutoff:
                stop = True
                break

            media = ep.get("media") or {}
            media_url = media.get("url")
            if not media_url or not ep.get("canDownload", True):
                continue

            title = safe_filename(f"{ep['title']}")
            ext = os.path.splitext(media_url.split("?")[0])[1] or ".mp3"
            dest = os.path.join(output_dir, f"{title}{ext}")

            print(f"[{ep['publishedAtText']}] {ep['title']}")
            download_file(media_url, dest, progress_callback=progress_callback)
            downloaded += 1

        if stop:
            break
        offset += 1
        time.sleep(0.5)

    print(f"\n총 {downloaded}개 에피소드를 확인/다운로드했습니다 (최근 {days}일 기준).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="팟빵 채널의 최근 에피소드를 자동 다운로드")
    parser.add_argument("channel_id", nargs="?", default="12757", help="팟빵 채널 ID (기본값: 12757)")
    parser.add_argument("--days", type=int, default=30, help="최근 며칠치를 받을지 (기본값: 30)")
    parser.add_argument("--output", default="./podcast", help="다운로드 폴더 (기본값: ./podcast)")
    args = parser.parse_args()

    download_recent_episodes(args.channel_id, args.days, args.output)
