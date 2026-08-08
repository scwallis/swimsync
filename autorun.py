import argparse
import ctypes
import os
import sys
import threading
import traceback

try:
    import tkinter as tk
except Exception:  # pragma: no cover
    tk = None

import config
import updater
from main_wnd import DummyMediaWindow


def get_volume_serial(path: str):
    root = os.path.splitdrive(os.path.abspath(path))[0] + "\\"
    serial = ctypes.c_uint32(0)
    ok = ctypes.windll.kernel32.GetVolumeInformationW(
        ctypes.c_wchar_p(root), None, 0, ctypes.byref(serial), None, None, None, 0
    )
    if not ok:
        return None
    return f"{serial.value:08X}"


class AutoRunner:
    def __init__(self, ui=None):
        self.ui = ui

    def run(self):
        selected_path = self.ui.get_selected_path() if self.ui is not None else os.path.abspath(config.SCRIPT_DIR)
        actual_serial = get_volume_serial(selected_path)
        if actual_serial != config.EXPECTED_VOLUME_SERIAL:
            config.log(f"드라이브 시리얼 불일치 (기대: {config.EXPECTED_VOLUME_SERIAL}, 실제: {actual_serial}) - 종료")
            if self.ui is not None:
                self.ui.set_status(f"드라이브 불일치: {actual_serial}")
            return

        if config.already_running_recently():
            config.log("최근에 이미 실행됨 (디바운스) - 종료")
            if self.ui is not None:
                self.ui.set_status("최근 실행되어 건너뜁니다.")
            return

        config.touch_lock()
        config.log("autorun 시작")

        if self.ui is not None:
            self.ui.set_status("유튜브 다운로드 중...")

        progress_callback = self.ui._on_progress if self.ui is not None else None

        try:
            youtube_urls = self.ui.get_youtube_urls() if self.ui is not None else [config.YOUTUBE_URL]
            podcast_urls = self.ui.get_podcast_urls() if self.ui is not None else [config.DEFAULT_PODCAST_URL]

            for youtube_url in youtube_urls:
                config.run_youtube_download(youtube_url, progress_callback=progress_callback)

            if self.ui is not None:
                self.ui.set_status("팟캐스트 다운로드 중...")

            for podcast_url in podcast_urls:
                channel_id = (
                    self.ui.extract_channel_id(podcast_url)
                    if self.ui is not None
                    else config.PODCAST_CHANNEL_ID
                )
                config.run_podcast_update(channel_id, progress_callback=progress_callback)

            if self.ui is not None:
                self.ui.reset_progress()
        except Exception:
            config.log(f"오류 발생:\n{traceback.format_exc()}")
            if self.ui is not None:
                self.ui.set_status("오류가 발생했습니다. 로그를 확인하세요.")
        else:
            config.log("autorun 종료")
            if self.ui is not None:
                self.ui.set_status("모든 작업 완료")


def main():
    parser = argparse.ArgumentParser(description="USB 드라이브 자동 미디어 다운로드")
    parser.add_argument("--no-ui", action="store_true", help="더미 Windows 창을 표시하지 않습니다.")
    args = parser.parse_args()

    ui = None if args.no_ui or tk is None or os.name != "nt" else DummyMediaWindow()
    runner = AutoRunner(ui)

    if ui is not None:
        thread = threading.Thread(target=runner.run, daemon=True)
        thread.start()
        ui.mainloop()
        return

    runner.run()


if __name__ == "__main__":
    try:
        update_result = updater.check_and_apply_update()
        if update_result == "restart":
            os.execv(sys.executable, [sys.executable] + sys.argv)
        if update_result is False:
            sys.exit(1)
        main()
    except Exception:
        config.log(f"치명적 오류:\n{traceback.format_exc()}")
