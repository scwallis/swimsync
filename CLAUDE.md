# SwimSync

## 개요
수영장에서 쓰는 MP3 플레이어에 동기화하기 위해 만든 미디어 다운로더.
- YouTube 영상을 MP3로 추출 (yt-dlp + ffmpeg)
- 팟빵(Podbbang) 팟캐스트 최근 에피소드 자동 다운로드
- GUI(Tkinter)로 URL 관리, 수동/자동 다운로드, 진행률 확인

## 파일 구조
```
E:\
├── autorun.py              # MainModule - AutoRunner(오케스트레이션) + entry point
├── main_wnd.py              # MainWnd - GUI 창(DummyMediaWindow) + UI 지원 함수
├── config.py                 # Config - 설정 상수 + log/lock/다운로드 트리거 공용 함수
├── downloader_youtube.py     # Downloader_Youtube - yt-dlp 기반 YouTube→MP3
├── downloader_podbbang.py    # Downloader_PodPang - 팟빵 API 다운로드
├── updater.py                 # Updater - 실행 시 GitHub(raw.githubusercontent.com)와 버전 비교, 구버전이면 자동 업데이트 후 재시작
├── release.py                  # 배포 도구 - 버전을 올리고 git commit/tag/push로 GitHub에 배포 (작업 완료 시 실행)
├── latest.txt                 # 저장소에 커밋되는 최신 버전 문자열 (updater.py가 참조)
├── .gitignore                 # mp3/, podcast/, ffmpeg_bin/, 로그/락 파일 등 제외
├── autorun.log               # 구조화 로그 (log() 함수가 남김)
├── console.log               # stdout/stderr 리다이렉트 (yt-dlp 출력, 콘솔 없는 실행 대비)
├── autorun.lock               # 중복 실행 방지용 락 파일 (120초 디바운스)
├── selected_path.txt         # GUI에서 선택한 다운로드 경로 저장
├── ffmpeg_bin/                # ffmpeg.exe, ffprobe.exe (최초 실행 시 자동 다운로드)
├── mp3/                       # 다운로드된 YouTube MP3
└── podcast/                   # 다운로드된 팟캐스트 에피소드
```

모듈 의존성: `downloader_youtube`/`downloader_podbbang`(leaf) ← `config`(공용 유틸) ← `main_wnd`(GUI) ← `autorun`(MainModule). 순환 참조 없음.

## 주요 설정 (config.py)
- `EXPECTED_VOLUME_SERIAL`: 대상 드라이브 검증용 볼륨 시리얼 (`8AFCE2B8`, 레이블 "X7")
- `YOUTUBE_URL` / `DEFAULT_PODCAST_URL`: 헤드리스(`--no-ui`) 실행 시 기본값. GUI에서는 Youtube(+)/Podcast(+)로 여러 URL 추가 가능
- `PODCAST_CHANNEL_ID` (`12757`), `PODCAST_DAYS` (30일)
- `DEBOUNCE_SECONDS` (120초), `AUTO_CHECK_INTERVAL_MS` (1시간 - GUI가 켜져 있는 동안 자동 재확인 주기)

## GUI 동작 방식
- 창 제목: **SwimSync**, 창이 열려 있는 동안 1시간마다 자동으로 YouTube/팟캐스트 재확인·다운로드
- "Auto Download" 버튼으로 수동 트리거 가능
- 다운로드 중에는 진행률 바 + 상태 텍스트(`42.3% (1.2MB / 2.8MB)`)로 표시 (yt-dlp progress_hooks / 팟캐스트는 청크 단위 계산). 진행률 콜백은 백그라운드 스레드에서 `root.after(0, ...)`로 메인 스레드에 위임해 Tk 스레드 안전성 확보, 0.2초 간격 스로틀링
- 상태바는 왼쪽(작업 상태) / 오른쪽(디스크 사용률)으로 분할되어 있어 서로 겹치지 않음

## 버전 관리 / 자동 업데이트
- 배포처: GitHub 공개 저장소 [scwallis/swimsync](https://github.com/scwallis/swimsync), `main` 브랜치 루트에 6개 스크립트 + `latest.txt` 커밋, 릴리스마다 `v<version>` 태그
- **작업 규칙**: 이 프로젝트에서 요청받은 작업이 완료되었다고 판단될 때마다 `python release.py [major|minor|patch]`(기본 patch)를 실행해 버전을 올리고 git commit/tag/push로 GitHub에 배포할 것
- **런타임 동작**: `autorun.py` 시작 시 `updater.check_and_apply_update()`가 `https://raw.githubusercontent.com/scwallis/swimsync/main/latest.txt`를 받아 로컬 `config.APP_VERSION`과 비교 (인증 불필요, public repo)
  - 최신이면 그대로 진행
  - 구버전이면 `main` 브랜치의 최신 파일들을 전부 메모리로 받은 뒤 한번에 덮어쓰고(부분 실패 방지) `os.execv`로 프로세스 재시작
  - GitHub 접근 실패/버전 정보 없음이면 실행을 차단(`sys.exit(1)`)하고 로그에 사유 기록
- 첫 `git push` 시 Git Credential Manager가 브라우저 GitHub 로그인 창을 띄울 수 있음

## 실행 방법
- `python autorun.py` — GUI 포함 실행 (콘솔 창이 함께 뜸)
- `pythonw.exe autorun.py` — 콘솔 창 없이 실행 (stdout/stderr는 `console.log`로 리다이렉트되어 크래시 없이 안전)
- `python autorun.py --no-ui` — GUI 없이 1회 다운로드만 수행 (스케줄러/CI용)

## 작업 규칙
- 스크립트 수정 후 반드시 `python autorun.py`(또는 `--no-ui`)로 정상 동작 확인
- mp3/, podcast/, ffmpeg_bin/ 폴더는 Git에 포함하지 않음
- 콘솔 없는 환경(pythonw 등)에서도 동작하도록 `sys.stdout`/`sys.stderr` None 체크 및 리다이렉트 유지
- 이 환경에서 `Write`/`Edit` 도구가 `E:\` 루트에 `EPERM` 오류를 내는 경우가 있어, 새 파일 생성/수정은 스크래치패드에 파이썬 스크립트를 작성해 실행하는 방식으로 우회함
- Windows 예약 작업(Scheduled Task) 자동 트리거는 제거됨 — 현재는 GUI 내 1시간 주기 자동 확인으로 대체

## 알려진 이슈
- yt-dlp 실행 시 JS 런타임 없다는 WARNING 발생 (deno 미설치) — 동작에는 지장 없음
- 같은 파일을 두 인스턴스가 동시에 받으면(.part → 최종 파일명 rename 시점 충돌) `PermissionError`가 날 수 있음 — 디바운스가 프로세스 간 동시 실행까지 완전히 막지는 않음, 우선순위 낮은 이슈

## 할 일
- [ ] GitHub 공개 저장소에 스크립트 코드 업로드 (사용자 요청으로 보류 중 - "천천히 진행하자")
- [ ] yt-dlp JS 런타임 경고 해결 (deno 설치 검토)

## 완료된 작업
- [x] Windows 더미 창(GUI) 구현, YouTube/Podcast URI 입력 + 확인(브라우저 열기) 버튼
- [x] Auto Download 버튼으로 수동 재다운로드
- [x] Youtube(+)/Podcast(+) 버튼으로 다중 URL 입력 지원, 왼쪽 아래 배치
- [x] 하단 상태바에 디스크 전체/사용/잔여 용량 표시, 상태 텍스트와 겹치지 않도록 좌우 분할
- [x] 창 제목을 "Media Auto Downloader" → "SwimSync"로 변경, 창 첫 줄에 배치
- [x] `podcast_downloader`의 `sys.stdout.reconfigure` None 크래시 수정
- [x] `DummyMediaWindow`에 누락된 `save_current_path` 메서드 추가
- [x] USB 이벤트 기반 예약 작업(Autorun_X7_USB) 제거, GUI 내 1시간 주기 자동 확인으로 전환
- [x] 콘솔 없는 실행 대비 stdout/stderr를 `console.log`로 리다이렉트, 최상위 예외도 로깅
- [x] MainModule/MainWnd/Config/Downloader_Youtube/Downloader_PodPang 5개 모듈로 구조 분리, 죽은 코드(get_available_drives, get_default_drive, 미사용 ttk import) 제거
- [x] 다운로드 진행률 바 + 퍼센트/용량 텍스트 표시
- [x] 버전 관리/자동 업데이트 기능 (updater.py, release.py)
- [x] 배포처를 D:\Storage → GitHub(scwallis/swimsync) 공개 저장소로 전환
- [x] Youtube(+)/Podcast(+) 클릭 시 창 높이 자동 증가
