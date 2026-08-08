import os
import re
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.py")
LATEST_PATH = os.path.join(SCRIPT_DIR, "latest.txt")

APP_FILES = [
    "config.py",
    "main_wnd.py",
    "autorun.py",
    "downloader_youtube.py",
    "downloader_podbbang.py",
    "updater.py",
]


def read_current_version():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    match = re.search(r'APP_VERSION = "([\d.]+)"', content)
    if not match:
        raise RuntimeError("config.py에서 APP_VERSION을 찾을 수 없습니다.")
    return match.group(1), content


def bump_version(version: str, part: str = "patch") -> str:
    major, minor, patch = (int(x) for x in version.split("."))
    if part == "major":
        major, minor, patch = major + 1, 0, 0
    elif part == "minor":
        minor, patch = minor + 1, 0
    else:
        patch += 1
    return f"{major}.{minor}.{patch}"


def write_new_version(content: str, old_version: str, new_version: str):
    updated = content.replace(f'APP_VERSION = "{old_version}"', f'APP_VERSION = "{new_version}"')
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        f.write(updated)


def write_latest_file(new_version: str):
    with open(LATEST_PATH, "w", encoding="utf-8") as f:
        f.write(new_version)


def run_git(*args):
    result = subprocess.run(
        ["git", *args], cwd=SCRIPT_DIR, capture_output=True, text=True, encoding="utf-8"
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} 실패:\n{result.stdout}\n{result.stderr}")
    return result.stdout


def publish(new_version: str):
    tracked = APP_FILES + ["latest.txt"]
    if os.path.isfile(os.path.join(SCRIPT_DIR, "CLAUDE.md")):
        tracked.append("CLAUDE.md")
    run_git("add", *tracked)
    run_git("commit", "-m", f"Release v{new_version}")
    run_git("tag", f"v{new_version}")
    run_git("push", "origin", "HEAD")
    run_git("push", "origin", f"v{new_version}")
    print(f"GitHub에 배포 완료: v{new_version}")


if __name__ == "__main__":
    part = sys.argv[1] if len(sys.argv) > 1 else "patch"
    old_version, content = read_current_version()
    new_version = bump_version(old_version, part)
    write_new_version(content, old_version, new_version)
    write_latest_file(new_version)
    publish(new_version)
    print(f"{old_version} -> {new_version}")
