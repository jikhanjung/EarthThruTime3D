# jikhanjung P11 — 현재의 바람·구름을 하루 한 번 새로

날짜: 2026-10-02 · 기준 버전: v0.24.1 · 앞: [jikhanjung P10](20261002_jikhanjung_P10_present_earth_in_flux.md)·
[109](20261002_jikhanjung_109_present_earth_in_flux.md) · 참고: GSM koprifossillab 005·013(`hourly.sh`, cron, `/healthz/`) ·
상태: 계획 — §4 정함

## 목적

v0.24 의 바람·구름은 판(release)을 만들 때 받은 한 시각에 고정돼 있다. 판을 자주 내지 않으면 몇 주씩 묵는다.
사람이 "해류는 당장은 모르겠지만 구름과 바람 정도는 하루에 한 번 정도 업데이트 하는 게 좋을 것 같네" 라고 했다.
**바람·구름만 하루 한 번** 새 시각으로 바꾸고, 해류(평년값)와 위성 바탕(Blue Marble)은 판 묶음에 그대로 둔다.

판 묶음은 바꾸지 않는다. 묶음 밖에 **새로 받은 것만 담는 자리**를 하나 두고, 앱은 그것이 온전하고 새것이면 쓰고,
없거나 깨졌거나 오래됐으면 묶음의 시각으로 물러선다. 받기가 며칠 실패해도 화면은 늘 무언가를 — 시각을 밝힌 채 —
보인다.

## 1. 지금 확인한 것 (2026-10-02)

- 운영 dolfinid-2(GCP asia-northeast3): Python 3.14.4·venv 있음, `sudo -n` 됨, 메모리 7.7 GB·2 코어, 디스크 여유 32 GB.
  NOMADS(`nomads.ncep.noaa.gov`)와 GMGSI 버킷 둘 다 서버에서 200.
- 컨테이너: 읽기 전용 루트, `/runtime`(판 묶음)은 읽기 전용, 쓰는 자리는 `./db` 하나(`docker-compose.yml`).
  호스트 타이머는 `earththrutime3d-backup.timer`(매시 DB 스냅숏) 하나다.
- `docs/operations.md`·`AGENTS.md` 의 자료 안전 약속: 묶음은 판마다 고정·해시 짝, 운영 DB 를 호스트에서 쓰지 않는다.
  P09 는 PBDB 를 매주 다시 받는 cron 을 **묶음을 다시 고정하는 일**이라 버렸다. 이 계획은 묶음을 건드리지 않으므로
  그 결정과 부딪히지 않는다 — 다만 "자료를 쓰는 두 번째 자리" 를 약속에 예외로 적어야 한다.
- 받는 코드: `scripts/fetch_present_weather.py`(v0.24) 가 GFS 분석과 같은 시의 GMGSI 를 받아 `present_catalogue` 의
  `weather` 절로 굽는다. numpy·Pillow·eccodes·h5py 가 든다. 앱 이미지에는 numpy 도 없다.
- 크기: 하루 한 시각에 PNG 넷 약 2.7 MB, 받는 원자료 약 17 MB(GRIB2 ≈ 10 MB, HDF5 ≈ 7.5 MB).

## 2. 설계

### 2.1 받는 곳 — 호스트 cron 이 컨테이너가 깔아 둔 스크립트를 호스트 venv 로 (GSM 방식)

사람이 정했다(2026-10-02): "fetch 용 컨테이너를 따로 올리는 것보다 /srv/EarthThruTime3D 아래 scripts 디렉토리 만들어서
ETT 컨테이너에서 cron 용 스크립트 복사해서 host 에서 cron 돌리고 container 실행 시킬 때 이미지 안에 들어있을 스크립트
변경사항 반영하게 해줘. cron 스크립트용 venv 는 호스트에 따로 만들어야지."

- 이미지에 cron 이 쓸 것을 함께 싣는다: `scripts/fetch_present_weather.py`·`scripts/present_catalogue.py`,
  `requirements-present.txt`(numpy·Pillow·eccodes·h5py 를 고정), `deploy/cron/*.sh`(`install.sh`·`present.sh`).
- **컨테이너가 뜰 때마다** entrypoint 가 `install.sh` 로 그것들을 `/srv/earththrutime3d/scripts/`(compose 로 쓰기 가능하게
  마운트)에 옮긴다. 판을 올리면 cron 이 도는 코드도 그 판이 된다. 자리가 없거나 쓸 수 없으면 건너뛴다 — 화면은 뜬다.
  운영 경로는 소문자 `/srv/earththrutime3d` 다.
- **venv 는 호스트가 따로 만든다** — `/srv/earththrutime3d/cron-venv/`(호스트 사용자 소유). `scripts/` 는 컨테이너(UID
  10001)가 쓰는 자리라 venv 를 그 안에 두지 않는다. `present.sh` 가 호스트 파이썬 판과 `requirements-present.txt` 의
  지문을 `cron-venv/.stamp` 에 적어, 바뀌면 다음 차례에 다시 만든다(GSM `run.sh` 와 같다, flock 으로 겹침 막음).
- 호스트 사용자 crontab 한 줄이 `present.sh` 를 부른다. 원자료(GRIB2·HDF5)는 임시 디렉터리에서 풀고 버린다.

### 2.2 쓰는 자리와 바꿔 끼우기 — `present-live/`

```
present-live/
  catalogue.json          # schema_version 1, "weather" 절 하나 (판 묶음과 같은 꼴)
  10m-<sha12>.png …       # 지금 시각의 넷
  previous/…              # 바로 앞 시각의 넷 (하루 더 남김)
  status.json             # 마지막 받기: at, result, cycle, note, last_ok
```

- 새 파일을 먼저 다 쓰고 검사한 뒤(크기, NaN 없음, u·v 범위, 이미지 크기) `catalogue.json` 을 원자적으로 바꾼다.
- **앞 시각의 파일은 하루 더 남긴다** — 바꿔 끼우기 직전에 연 쪽은 앞 주소를 부른다. 그다음 받기 때 지운다.
- 실패하면 아무것도 바꾸지 않고 `status.json` 에만 적는다. 받기 스크립트의 `--out` 이 이 자리를 가리키게 고친다
  (지금은 `data/derived/present-earth` 고정).

### 2.3 앱 — 새것이면 쓰고, 아니면 묶음으로

- compose 에 `./present-live → /present-live` 를 **읽기 전용**으로 더한다. 설정 `PRESENT_LIVE_DIR`(기본 없음).
- `core/present.py` 의 `weather` 절: `PRESENT_LIVE_DIR` 의 카탈로그가 같은 검사를 통과하고, 그 `t` 가 묶음의 `t` 보다
  새롭고, **48 시간 안**이면 그것을 쓴다. 아니면 묶음의 것. 내주기(`/present/assets/`)는 두 자리를 다 찾는다(앞 시각의
  파일 포함). 해시 검사·불변 캐시는 그대로 — 파일 이름에 sha 가 들어 있어 하루마다 주소가 바뀐다.
- 쪽(HTML)은 카탈로그를 매 요청 읽는다(`read_json` 이 파일 정체로 캐시). 따로 다시 띄울 일이 없다.
- **화면의 말** — 안내문 "이 판을 만들 때 받은 한 시각" 을 출처에 따라 바꾼다: 새로 받은 것이면 "하루 한 번 받는
  최신 분석 — 실시간이 아닙니다", 묶음으로 물러섰으면 지금 문장. 시각 줄은 그대로 `t` 에서만.
- `/healthz` 에 `present_live: {t, age_h, source: live|bundle, last_ok}` 를 **정보로만** 싣는다. 받기가 늦어도 503·degraded
  로 만들지 않는다 — 선택 레이어이고 묶음이 받쳐 준다. `smoke.sh` 는 건드리지 않는다.

### 2.4 시각과 이웃 예절

- 하루 한 번 **12 UTC 주기의 분석**을 **17:10 UTC(02:10 KST)** 에 받는다(사람이 정했다). NOMADS 에 주기 뒤 약
  3.5–4 시간에 올라온다. 그날 12 UTC 가 아직 없으면 가장 새 주기로 물러선다. GMGSI 는 같은 시.
- 요청은 하루에 NOMADS 1 번 + S3 목록 1 번 + 파일 1 번. 실패하면 그날은 쉬고 다음 날 다시(재시도 3 번까지만).

### 2.5 자료 안전·운영

- `docs/operations.md` 에 예외로 적는다: `present-live/` 는 **다시 만들 수 있는 자료**라 백업하지 않고(오프사이트 미러도
  제외), `prune.sh` 가 건드리지 않으며, 코드 롤백은 이 자리를 건드리지 않는다. 지우면 다음 받기까지 묶음의 시각이 보일
  뿐이다. 운영 DB·비밀·판 묶음은 이 작업과 무관하다.
- 롤백: 앞 판으로 되돌려도 compose 의 마운트는 남는다 — 앞 판의 앱은 `PRESENT_LIVE_DIR` 를 모르니 마운트를 무시한다.
- cron 한 줄(`deploy/host/crontab.earththrutime3d`)과 처음 한 번 할 일(`scripts/`·`present-live/`·`cron-venv/` 만들기 —
  `scripts/` 는 UID 10001 이 쓰도록 `sudo install -d -o 10001`)을 `deploy/README.md` 에 적는다.
- egress: 하루 한 번 주소가 바뀌어 켠 사람의 브라우저가 하루에 한 번 새로 받는다(바람 0.8 MB·구름 0.6 MB 남짓).

## 3. 단계 (PR 하나씩)

1. **받기 스크립트** — `--out`, `--hour 12`, 검사, 앞 시각 남기기, `status.json`, `requirements-present.txt`,
   `deploy/cron/install.sh`·`present.sh`, 이미지에 싣고 entrypoint 가 옮기기. 화면 변화 없음.
2. **앱** — `PRESENT_LIVE_DIR`, 새것/묶음 고르기, 두 자리 내주기, 안내문 둘, `/healthz` 정보, 시험(새것·오래된 것·깨진 것·
   앞 시각 주소). CHANGELOG.
3. **호스트** — compose 마운트(`scripts/` 쓰기, `present-live/` 읽기 전용), crontab 한 줄, `deploy/README.md`·
   `docs/operations.md`. 판 v0.25.0 으로 배포하고 그날 17:10 UTC 의 첫 받기를 확인한다.

## 4. 정한 것 (2026-10-02)

- **(가) 받는 곳** — 받기 전용 컨테이너(처음 추천) 대신 **호스트 cron + 컨테이너가 옮긴 스크립트 + 호스트 venv**(§2.1).
- **(나) 시각** — **12 UTC 분석, 17:10 UTC(02:10 KST)**.
- **(다) 묶음으로 물러서는 나이** — 48 시간(추천대로, 따로 말이 없었다).
- (라) 더 자주 — 지금은 하루 한 번.

## 5. 확인하는 법

- 개발 호스트: `present-live/` 를 임시 자리로 두고 받기 컨테이너를 돌려 카탈로그·파일·`status.json` 을 본다. 일부러 깬
  카탈로그·49 시간 전 `t`·앞 시각 주소로 앱 시험.
- 운영: cron 을 건 날 `logs/present.log`·`present-live/status.json` 으로 17:10 UTC 받기 성공,
  공개 화면의 시각 줄이 그날 12 UTC, `/healthz` 의 `present_live.source = live`. 받기를 멈춰 두고 48 시간 뒤 `bundle` 로
  물러서는 것은 개발 호스트 시험으로 대신한다.
