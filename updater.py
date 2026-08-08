import os
import urllib.error
import urllib.request

import config


def _fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "SwimSync-Updater"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.read().decode("utf-8")


def _fetch_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "SwimSync-Updater"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.read()


def check_and_apply_update():
    """Return True if already up to date, "restart" if updated and needs a
    process restart to pick up new code, or False if the update could not
    be verified (caller should refuse to run)."""
    try:
        latest_version = _fetch_text(config.LATEST_URL).strip()
    except (OSError, urllib.error.URLError):
        config.log(f"업데이트 서버({config.LATEST_URL})에 접근할 수 없어 실행을 중단합니다.")
        return False

    if not latest_version:
        config.log("최신 버전 정보가 비어 있어 실행을 중단합니다.")
        return False

    if latest_version == config.APP_VERSION:
        return True

    downloaded = {}
    try:
        for filename in config.APP_FILES:
            url = f"{config.RAW_BASE_URL}/{filename}"
            downloaded[filename] = _fetch_bytes(url)
    except (OSError, urllib.error.URLError):
        config.log(f"버전 {latest_version} 다운로드 실패, 실행을 중단합니다.")
        return False

    try:
        for filename, data in downloaded.items():
            dst = os.path.join(config.SCRIPT_DIR, filename)
            with open(dst, "wb") as f:
                f.write(data)
    except OSError:
        config.log(f"버전 {latest_version} 적용 중 오류가 발생해 실행을 중단합니다.")
        return False

    config.log(f"버전 {config.APP_VERSION} -> {latest_version} 업데이트 완료. 재시작합니다.")
    return "restart"
