# jikhanjung 115 — 현재의 바람·구름을 하루 한 번 새로

날짜: 2026-10-02 · 계획: [jikhanjung P11](20261002_jikhanjung_P11_daily_present_weather.md) · PR: #108

P11 의 1–3 단계를 한 PR 로 했다. 사람이 정한 대로 받기 전용 컨테이너 대신 **호스트 cron + 컨테이너가 옮겨 둔 스크립트 +
호스트 venv** 로, 시각은 **12 UTC 분석을 17:10 UTC(02:10 KST)** 에 받는다.

## 1. 받기 스크립트

- `scripts/fetch_present_weather.py` 에 `--live DIR` 과 `--hour HH` 를 더했다. `--live` 는 같은 `weather` 절을 DIR 에 쓰되
  원자료를 남기지 않고(`data/sources/` 에 쓰지 않음), `sources/present_weather.json` 도 건드리지 않으며, `status.json`
  (`at`·`result`·`t`·`last_ok`·`note`)을 남긴다. 실패도 적고 앞의 좋은 시각은 그대로 둔다. `--hour 12` 는 그날 12 UTC 가
  시작됐으면 그것, 아니면 전날 12 UTC 를 받는다 — 하루의 시각을 고정한다.
- 바꿔 끼우기 전 검사(`check`): 바람 빠르기가 유한하고 최대 150 m/s 밑·평균 0.5 m/s 위, 구름량 평균 0.05–0.95.
- `present_catalogue.write_section(out=, keep_previous=True)`: 앞 시각의 파일을 `previous` 로 하루 더 남기고 그보다
  오래된 것은 지운다. 파일·카탈로그는 0644 로 쓴다(컨테이너가 다른 UID 로 읽는다).

## 2. 옮기기와 cron

- `deploy/cron/install.sh`(sh): entrypoint 가 검증 뒤 부른다. 이미지 안의 `present.sh`·받기 코드 둘·
  `requirements-present.txt` 와 `INSTALLED`(판·시각)를 `PRESENT_SCRIPTS_DIR`(`/cron-scripts` = 호스트 `scripts/`)에
  파일마다 통째로 바꿔 넣는다. 자리가 없거나 쓸 수 없으면 말만 하고 넘어간다 — 화면은 뜬다.
- `deploy/cron/present.sh`(bash, 호스트): `cron-venv/` 를 호스트 파이썬 판 + requirements 지문(`.stamp`)이 바뀌면 다시
  만들고, flock 으로 겹침을 막고, `timeout 1200` 으로 받는다. GSM `run.sh` 를 줄인 것이다.
- `requirements-present.txt`: numpy 2.4.6, Pillow 12.3.0, eccodes 2.49.0, h5py 3.16.0. 앱 이미지에는 깔지 않는다.
- `deploy/host/crontab.earththrutime3d`: `10 17 * * * …/scripts/present.sh >> …/logs/present.log 2>&1`. 서버는 UTC 다.
- compose: `./present-live → /present-live`(읽기 전용), `./scripts → /cron-scripts`. `deploy.sh` 가 `present-live`·
  `scripts`·`logs` 를 만든다(처음 `scripts/` 는 `sudo install -d -o 10001` 로 컨테이너가 쓰게 — `deploy/README.md`).

## 3. 앱

- `PRESENT_LIVE_DIR`(이미지 기본 `/present-live`). `core/present.py` 가 그 카탈로그의 `weather` 절을 같은 검사로 읽어,
  판의 시각보다 새롭고 48 시간(`LIVE_MAX_AGE`) 안이면 그것을 쓴다. 아니면 판의 것. 절마다 `root`(파일 자리)와
  `source`(`live`·`release`)를 단다. 내주기는 지금·앞 시각의 파일을 다 찾는다.
- 정보 패널 안내가 출처를 따른다: live 면 "하루 한 번(한국 시각 새벽 2시 무렵) 받는 그날 12 UTC의 분석", 아니면 "이 판을
  만들 때 받은 한 시각". 시각 줄과 범례는 전처럼 `t` 에서만.
- `/healthz` 에 `present: {source, t, age_h, refresh}` — 정보만. 상태·HTTP 코드는 바꾸지 않는다(`smoke.sh` 그대로).

## 4. 확인한 것

- `core/test_present.py` 의 live 시험 4 개: 새 시각이 판의 것을 대신함·앞 시각 파일 내주기·판의 바탕과 해류는 그대로,
  49 시간 전·파일 빠짐·깨진 카탈로그면 판으로, 판보다 오래된 시각은 무시, 쪽의 안내(한·영). Django 96 개, npm 49 개.
- 개발 호스트에서 `--live` 를 두 번(12 UTC, 18 UTC) 돌려 현재·앞 시각 넷씩과 `status.json`, 원자료 없음을 보았다.
- **운영 서버의 `/tmp` 에서** `present.sh` 를 돌렸다(실제 Python 3.14.4): venv 만들기 17 초(295 MB), 첫 받기 32 초,
  두 번째는 venv 를 다시 쓰고 18 초. 시험 디렉터리는 지웠다.
