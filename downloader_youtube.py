import subprocess
import sys
import os
import urllib.request
import zipfile
import shutil


FFMPEG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg_bin")
FFMPEG_ZIP_URL = (
    "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/"
    "ffmpeg-master-latest-win64-gpl.zip"
)


def install_dependencies():
    for pkg in ["yt-dlp"]:
        print(f"Installing {pkg}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])


def find_in_path(name):
    return shutil.which(name)


def download_ffmpeg():
    os.makedirs(FFMPEG_DIR, exist_ok=True)
    zip_path = os.path.join(FFMPEG_DIR, "ffmpeg.zip")

    print("Downloading FFmpeg binaries (one-time setup)...")
    urllib.request.urlretrieve(FFMPEG_ZIP_URL, zip_path)

    print("Extracting ffmpeg.exe and ffprobe.exe...")
    with zipfile.ZipFile(zip_path, "r") as z:
        for name in z.namelist():
            basename = os.path.basename(name)
            if basename in ("ffmpeg.exe", "ffprobe.exe"):
                data = z.read(name)
                dest = os.path.join(FFMPEG_DIR, basename)
                with open(dest, "wb") as f:
                    f.write(data)
                print(f"  Extracted: {basename}")

    os.remove(zip_path)
    print(f"FFmpeg ready at: {FFMPEG_DIR}\n")


def get_ffmpeg_location():
    # Use system ffmpeg if available
    if find_in_path("ffmpeg") and find_in_path("ffprobe"):
        return None  # yt-dlp will find them automatically

    ffmpeg_exe = os.path.join(FFMPEG_DIR, "ffmpeg.exe")
    ffprobe_exe = os.path.join(FFMPEG_DIR, "ffprobe.exe")

    if not (os.path.isfile(ffmpeg_exe) and os.path.isfile(ffprobe_exe)):
        download_ffmpeg()

    return FFMPEG_DIR


def _make_progress_hook(progress_callback):
    def hook(d):
        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes", 0)
            percent = (downloaded / total * 100) if total else 0.0
            progress_callback(percent, downloaded, total)
        elif status == "finished":
            total = d.get("total_bytes") or d.get("downloaded_bytes", 0)
            progress_callback(100.0, total, total)

    return hook


def download_mp3(url: str, output_dir: str = ".", use_archive: bool = True, progress_callback=None):
    try:
        import yt_dlp
    except ImportError:
        install_dependencies()
        import yt_dlp

    os.makedirs(output_dir, exist_ok=True)

    ffmpeg_location = get_ffmpeg_location()

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(output_dir, "%(title)s.%(ext)s"),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "quiet": False,
        "no_warnings": False,
    }

    if ffmpeg_location:
        ydl_opts["ffmpeg_location"] = ffmpeg_location

    if use_archive:
        ydl_opts["download_archive"] = os.path.join(output_dir, ".download_archive.txt")

    if progress_callback is not None:
        ydl_opts["progress_hooks"] = [_make_progress_hook(progress_callback)]

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        print(f"Downloading: {url}\n")
        info = ydl.extract_info(url, download=True)
        if info is None:
            print("\n이미 다운로드된 항목입니다 (archive에 기록됨). 건너뜀.")
            return
        title = info.get("title", "Unknown")
        print(f"\nDone! Saved as: {title}.mp3")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python downloader_youtube.py <youtube_url> [output_dir]")
        print("Example: python downloader_youtube.py https://www.youtube.com/watch?v=xxxxx ./downloads")
        sys.exit(1)

    url = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "./mp3"

    download_mp3(url, output_dir)
