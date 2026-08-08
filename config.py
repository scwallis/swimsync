import os
import sys
import time
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

EXPECTED_VOLUME_SERIAL = "8AFCE2B8"  # E: drive, label "X7"
LOG_FILE = os.path.join(SCRIPT_DIR, "autorun.log")
LOCK_FILE = os.path.join(SCRIPT_DIR, "autorun.lock")
CONSOLE_LOG_FILE = os.path.join(SCRIPT_DIR, "console.log")
DEBOUNCE_SECONDS = 120
AUTO_CHECK_INTERVAL_MS = 60 * 60 * 1000  # 1시간마다 자동 확인

YOUTUBE_URL = "https://www.youtube.com/watch?v=GvtNBLn6_Ik"
YOUTUBE_OUTPUT = os.path.join(SCRIPT_DIR, "mp3")

PODCAST_CHANNEL_ID = "12757"
PODCAST_DAYS = 30
PODCAST_OUTPUT = os.path.join(SCRIPT_DIR, "podcast")
DEFAULT_PODCAST_URL = f"https://www.podbbang.com/channels/{PODCAST_CHANNEL_ID}"

PATH_FILE = os.path.join(SCRIPT_DIR, "selected_path.txt")

APP_VERSION = "1.0.2"
GITHUB_REPO = "scwallis/swimsync"
RAW_BASE_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main"
LATEST_URL = f"{RAW_BASE_URL}/latest.txt"
APP_FILES = [
    "config.py",
    "main_wnd.py",
    "autorun.py",
    "downloader_youtube.py",
    "downloader_podbbang.py",
    "updater.py",
]


def _redirect_console_output():
    try:
        log_stream = open(CONSOLE_LOG_FILE, "a", encoding="utf-8", buffering=1)
    except OSError:
        return
    sys.stdout = log_stream
    sys.stderr = log_stream


_redirect_console_output()


def log(message: str):
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {message}"
    if sys.stdout is not None:
        print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def already_running_recently() -> bool:
    if not os.path.exists(LOCK_FILE):
        return False
    age = time.time() - os.path.getmtime(LOCK_FILE)
    return age < DEBOUNCE_SECONDS


def touch_lock():
    with open(LOCK_FILE, "w", encoding="utf-8") as f:
        f.write(str(time.time()))


def run_youtube_download(url: str = YOUTUBE_URL, progress_callback=None):
    import downloader_youtube
    log(f"유튜브 다운로드 시작: {url}")
    downloader_youtube.download_mp3(url, YOUTUBE_OUTPUT, progress_callback=progress_callback)
    log("유튜브 다운로드 완료")


def run_podcast_update(channel_id: str = PODCAST_CHANNEL_ID, progress_callback=None):
    import downloader_podbbang
    log(f"팟캐스트 업데이트 시작: 채널 {channel_id}")
    downloader_podbbang.download_recent_episodes(
        channel_id, PODCAST_DAYS, PODCAST_OUTPUT, progress_callback=progress_callback
    )
    log("팟캐스트 업데이트 완료")
