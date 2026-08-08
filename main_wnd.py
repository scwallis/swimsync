import os
import re
import shutil
import threading
import time
import traceback
import webbrowser

try:
    import tkinter as tk
    from tkinter import filedialog, ttk
except Exception:  # pragma: no cover
    tk = None
    ttk = None
    filedialog = None

import config

ROW_HEIGHT_PX = 34


def get_default_path():
    return os.path.abspath(config.SCRIPT_DIR)


def load_selected_path():
    try:
        if os.path.exists(config.PATH_FILE):
            with open(config.PATH_FILE, "r", encoding="utf-8") as f:
                value = f.read().strip()
                if value and os.path.isdir(value):
                    return value
    except OSError:
        pass
    return get_default_path()


def save_selected_path(path_value: str):
    try:
        normalized = (path_value or "").strip()
        if not normalized:
            return
        os.makedirs(normalized, exist_ok=True)
        with open(config.PATH_FILE, "w", encoding="utf-8") as f:
            f.write(normalized)
    except OSError:
        pass


def get_selected_path_from_var(path_var):
    value = (path_var.get() or "").strip()
    return value or get_default_path()


def format_size(value_bytes: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(value_bytes)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024.0
    return f"{value:.1f} TB"


def get_drive_usage(path: str):
    root = os.path.splitdrive(os.path.abspath(path))[0]
    if not root:
        return {
            "drive": "",
            "total": 0,
            "used": 0,
            "free": 0,
            "percent_used": 0,
        }
    drive_root = root + "\\"
    try:
        total, used, free = shutil.disk_usage(drive_root)
    except OSError:
        return {
            "drive": drive_root,
            "total": 0,
            "used": 0,
            "free": 0,
            "percent_used": 0,
        }
    return {
        "drive": drive_root,
        "total": total,
        "used": used,
        "free": free,
        "percent_used": (used / total * 100) if total else 0,
    }


class DummyMediaWindow:
    def __init__(self):
        if tk is None or os.name != "nt":
            self.root = None
            return

        self.root = tk.Tk()
        self.root.title("SwimSync")
        self.root.geometry("620x300")
        self.root.minsize(520, 250)
        self.root.configure(bg="#111827")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.attributes("-topmost", True)

        self.path_var = tk.StringVar(value=load_selected_path())
        self.youtube_vars = [tk.StringVar(value=config.YOUTUBE_URL)]
        self.podcast_vars = [tk.StringVar(value=config.DEFAULT_PODCAST_URL)]
        self.status_var = tk.StringVar(value="대기 중")
        self.disk_status_var = tk.StringVar(value="디스크 용량 로딩 중...")
        self.progress_var = tk.DoubleVar(value=0)
        self._disk_refresh_job = None
        self._last_progress_update = 0.0

        title = tk.Label(
            self.root,
            text="SwimSync",
            bg="#111827",
            fg="#F9FAFB",
            font=("Malgun Gothic", 14, "bold"),
            pady=10,
        )
        title.pack(fill="x")

        drive_row = tk.Frame(self.root, bg="#111827")
        drive_row.pack(fill="x", padx=12, pady=(8, 6))

        drive_label = tk.Label(
            drive_row,
            text="Path",
            bg="#111827",
            fg="#E5E7EB",
            width=10,
            anchor="w",
            font=("Malgun Gothic", 10),
        )
        drive_label.pack(side="left")

        path_entry = tk.Entry(
            drive_row,
            textvariable=self.path_var,
            width=34,
            font=("Malgun Gothic", 10),
        )
        path_entry.pack(side="left", padx=(8, 6), fill="x", expand=True)
        path_entry.bind("<FocusOut>", self.save_current_path)

        browse_button = tk.Button(
            drive_row,
            text="Browse",
            command=self.browse_path,
            bg="#4B5563",
            fg="white",
            activebackground="#374151",
            relief="flat",
            width=8,
        )
        browse_button.pack(side="right")

        self.youtube_frame = tk.Frame(self.root, bg="#111827")
        self.youtube_frame.pack(fill="x", padx=12, pady=(0, 6))
        self.create_url_row(self.youtube_frame, "YouTube", self.youtube_vars[0])

        self.podcast_frame = tk.Frame(self.root, bg="#111827")
        self.podcast_frame.pack(fill="x", padx=12, pady=(0, 10))
        self.create_url_row(self.podcast_frame, "Podcast", self.podcast_vars[0])

        toolbar = tk.Frame(self.root, bg="#111827")
        toolbar.pack(fill="x", padx=12, pady=(0, 12))

        left_controls = tk.Frame(toolbar, bg="#111827")
        left_controls.pack(side="left")

        self.youtube_add = tk.Button(
            left_controls,
            text="Youtube (+)",
            command=self.add_youtube_row,
            bg="#374151",
            fg="white",
            activebackground="#4B5563",
            relief="flat",
            font=("Malgun Gothic", 9),
        )
        self.youtube_add.pack(side="left", padx=(0, 8))

        self.podcast_add = tk.Button(
            left_controls,
            text="Podcast (+)",
            command=self.add_podcast_row,
            bg="#374151",
            fg="white",
            activebackground="#4B5563",
            relief="flat",
            font=("Malgun Gothic", 9),
        )
        self.podcast_add.pack(side="left")

        right_controls = tk.Frame(toolbar, bg="#111827")
        right_controls.pack(side="right")

        self.auto_button = tk.Button(
            right_controls,
            text="Auto Download",
            command=self.run_manual_download,
            bg="#10B981",
            fg="white",
            activebackground="#059669",
            relief="flat",
            width=14,
            height=2,
            font=("Malgun Gothic", 10, "bold"),
        )
        self.auto_button.pack(anchor="e")

        self.progress_bar = ttk.Progressbar(
            self.root,
            orient="horizontal",
            mode="determinate",
            variable=self.progress_var,
            maximum=100,
        )
        self.progress_bar.pack(fill="x", padx=12, pady=(0, 8))

        status_bar = tk.Frame(self.root, bg="#1F2937")
        status_bar.pack(fill="x", side="bottom")

        self.disk_bar = tk.Label(
            status_bar,
            textvariable=self.disk_status_var,
            bg="#1F2937",
            fg="#E5E7EB",
            font=("Malgun Gothic", 9),
            padx=12,
            pady=8,
            anchor="e",
            justify="right",
        )
        self.disk_bar.pack(side="right")

        status = tk.Label(
            status_bar,
            textvariable=self.status_var,
            bg="#1F2937",
            fg="#D1FAE5",
            font=("Malgun Gothic", 10),
            padx=12,
            pady=8,
            anchor="w",
            justify="left",
        )
        status.pack(side="left", fill="x", expand=True)

        self.refresh_disk_status()
        self.schedule_periodic_check()

        self.root.update_idletasks()
        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", False)

    def schedule_periodic_check(self):
        if self.root is not None and self.root.winfo_exists():
            self.root.after(config.AUTO_CHECK_INTERVAL_MS, self.run_periodic_check)

    def run_periodic_check(self):
        thread = threading.Thread(target=self._periodic_download_worker, daemon=True)
        thread.start()
        self.schedule_periodic_check()

    def _periodic_download_worker(self):
        try:
            youtube_urls = self.get_youtube_urls()
            podcast_urls = self.get_podcast_urls()
            config.touch_lock()
            config.log(f"주기적 확인 시작: YouTube={youtube_urls}, Podcast={podcast_urls}")
            self.set_status("주기적 확인 중...")
            self.reset_progress()

            for youtube_url in youtube_urls:
                config.run_youtube_download(youtube_url, progress_callback=self._on_progress)

            for podcast_url in podcast_urls:
                channel_id = self.extract_channel_id(podcast_url)
                config.run_podcast_update(channel_id, progress_callback=self._on_progress)

            self.reset_progress()
            self.set_status("주기적 확인 완료")
            config.log("주기적 확인 종료")
        except Exception:
            config.log(f"주기적 확인 오류:\n{traceback.format_exc()}")
            self.set_status("주기적 확인 실패")

    def get_selected_path(self):
        if self.root is None:
            return load_selected_path()
        value = get_selected_path_from_var(self.path_var)
        if not os.path.isdir(value):
            return get_default_path()
        return value

    def save_current_path(self, event=None):
        save_selected_path(get_selected_path_from_var(self.path_var))

    def browse_path(self):
        if filedialog is None:
            return
        selected = filedialog.askdirectory(title="폴더 선택")
        if selected:
            self.path_var.set(selected)
            save_selected_path(selected)
            self.refresh_disk_status()

    def refresh_disk_status(self):
        path = self.get_selected_path()
        usage = get_drive_usage(path)
        if usage["total"] <= 0:
            self.disk_status_var.set("디스크 용량 정보를 가져올 수 없습니다.")
        else:
            percent = usage["percent_used"]
            label = (
                f"{usage['drive']} | "
                f"전체: {format_size(usage['total'])} | "
                f"사용: {format_size(usage['used'])} | "
                f"여유: {format_size(usage['free'])} | "
                f"사용률: {percent:.1f}%"
            )
            self.disk_status_var.set(label)
        if self.root is not None and self.root.winfo_exists():
            self._disk_refresh_job = self.root.after(5000, self.refresh_disk_status)

    def add_youtube_row(self):
        var = tk.StringVar(value="")
        self.youtube_vars.append(var)
        self.create_url_row(self.youtube_frame, "YouTube", var)
        self.grow_window(ROW_HEIGHT_PX)

    def add_podcast_row(self):
        var = tk.StringVar(value="")
        self.podcast_vars.append(var)
        self.create_url_row(self.podcast_frame, "Podcast", var)
        self.grow_window(ROW_HEIGHT_PX)

    def grow_window(self, delta_height: int):
        if self.root is None:
            return
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        self.root.geometry(f"{width}x{height + delta_height}")

    def create_url_row(self, parent, label_text, value_var):
        row = tk.Frame(parent, bg="#111827")
        row.pack(fill="x", pady=4)

        label = tk.Label(
            row,
            text=label_text,
            bg="#111827",
            fg="#E5E7EB",
            width=10,
            anchor="w",
            font=("Malgun Gothic", 10),
        )
        label.pack(side="left")

        entry = tk.Entry(
            row,
            textvariable=value_var,
            width=44,
            font=("Malgun Gothic", 10),
        )
        entry.pack(side="left", padx=(8, 6), fill="x", expand=True)

        button = tk.Button(
            row,
            text="확인",
            command=lambda: self.open_url(value_var.get()),
            width=8,
            bg="#2563EB",
            fg="white",
            activebackground="#1D4ED8",
            relief="flat",
        )
        button.pack(side="right")

    def get_youtube_urls(self):
        values = [var.get().strip() for var in self.youtube_vars]
        filtered = [value for value in values if value]
        return filtered or [config.YOUTUBE_URL]

    def get_podcast_urls(self):
        values = [var.get().strip() for var in self.podcast_vars]
        filtered = [value for value in values if value]
        return filtered or [config.DEFAULT_PODCAST_URL]

    def open_url(self, url: str):
        if not url:
            return
        try:
            webbrowser.open(url, new=2)
            self.status_var.set(f"브라우저에서 열기: {url}")
        except Exception:
            self.status_var.set("URL 열기에 실패했습니다.")
            config.log(f"브라우저 열기 실패: {url}")

    def set_status(self, text: str):
        if self.root is not None and self.root.winfo_exists():
            self.status_var.set(text)
            self.root.update_idletasks()
            self.root.update()

    def reset_progress(self):
        if self.root is not None and self.root.winfo_exists():
            self.root.after(0, self.progress_var.set, 0)

    def _on_progress(self, percent, downloaded, total):
        now = time.time()
        if percent < 100 and now - self._last_progress_update < 0.2:
            return
        self._last_progress_update = now
        if self.root is not None and self.root.winfo_exists():
            self.root.after(0, self._apply_progress, percent, downloaded, total)

    def _apply_progress(self, percent, downloaded, total):
        self.progress_var.set(percent)
        size_text = f"{format_size(downloaded)} / {format_size(total)}" if total else format_size(downloaded)
        self.status_var.set(f"다운로드 중... {percent:.1f}% ({size_text})")

    def on_close(self):
        self.set_status("종료 대기 중")
        self.root.destroy()

    def run_manual_download(self):
        if self.root is None:
            return

        self.set_status("수동 다운로드 시작...")

        thread = threading.Thread(
            target=self._manual_download_worker,
            daemon=True,
        )
        thread.start()

    def _manual_download_worker(self):
        try:
            youtube_urls = self.get_youtube_urls()
            podcast_urls = self.get_podcast_urls()
            config.touch_lock()
            config.log(f"수동 다운로드 시작: YouTube={youtube_urls}, Podcast={podcast_urls}")
            self.reset_progress()

            for youtube_url in youtube_urls:
                config.run_youtube_download(youtube_url, progress_callback=self._on_progress)

            for podcast_url in podcast_urls:
                channel_id = self.extract_channel_id(podcast_url)
                config.run_podcast_update(channel_id, progress_callback=self._on_progress)

            self.reset_progress()
            self.set_status("수동 다운로드 완료")
            config.log("수동 다운로드 종료")
        except Exception:
            config.log(f"수동 다운로드 오류:\n{traceback.format_exc()}")
            self.set_status("수동 다운로드 실패")

    @staticmethod
    def extract_channel_id(url: str):
        if not url:
            return config.PODCAST_CHANNEL_ID
        value = url.strip()
        if value.isdigit():
            return value
        match = re.search(r"/channels/(\d+)", value, re.IGNORECASE)
        if match:
            return match.group(1)
        match = re.search(r"channel_id[=/:]?(\d+)", value, re.IGNORECASE)
        if match:
            return match.group(1)
        return config.PODCAST_CHANNEL_ID

    def mainloop(self):
        if self.root is not None:
            self.root.mainloop()
