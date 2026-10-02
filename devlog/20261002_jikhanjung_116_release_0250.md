# v0.25.0 — 현재의 바람·구름 하루 한 번 받기 릴리스

상태: 2026-10-02 운영 배포·첫 받기 완료. 첫 `live` 전환은 그날 17:10 UTC 받기에서.

## 변경

- [#108](https://github.com/jikhanjung/EarthThruTime3D/pull/108) 호스트 cron 이 매일 17:10 UTC 에 그날 12 UTC 분석을
  `present-live/` 에 받고, 앱이 새것이면 쓴다([jikhanjung P11](20261002_jikhanjung_P11_daily_present_weather.md)·
  [115](20261002_jikhanjung_115_daily_present_weather.md)). 자료 묶음은 v0.24.0 과 같다. **호스트 묶음이 바뀐다**
  (compose 마운트, `deploy.sh`, `crontab.earththrutime3d`) — 처음 한 번 할 일은 `deploy/README.md`.

## 빌드에서 고친 것

첫 빌드 뒤 이미지 안을 열어 보니 `scripts/fetch_present_weather.py`·`present_catalogue.py` 가 **0 바이트**였다.
`.dockerignore` 끝의 `scripts/` 가 앞의 `!scripts/...` 예외를 덮어, 이름이 적힌 파일이 빈 파일로 들어간다. 9 월부터
이미지의 `compile_messages.py` 도 빈 파일이었고(빌드의 번역 컴파일은 아무것도 하지 않았으며 `.mo` 는 체크아웃에서
따라 들어갔다) 아무도 몰랐다. 예외를 `scripts/` 뒤로 옮겨(main `Ship the scripts the image names…`) 다시 빌드했다.

## 빌드·운영 배포

- main 에서 `build.sh v0.25.0`(두 번째). Django 96 개, 자료 1,297 개(v0.24.0 과 같다), 이미지 스모크 통과. 이미지 안의
  스크립트 크기(3,788 · 14,788 · 2,677 bytes)를 확인했다.
- 이미지 digest `sha256:a19601b61b33e4f6ae5fbbcfb67c95c1d0b829c5aa60eadc0db26bfa897d0563`. Docker Hub push, digest 로 pull.
  호스트 묶음은 `docker-compose.yml`·`deploy.sh`·`crontab.earththrutime3d` 셋이 달라 그 셋만 풀었다(앞 것은 배포 성공까지 사본으로 두었다).
- 처음 한 번: `sudo install -d -o 10001 -g honestjung -m 2775 scripts`, `present-live`·`logs`.
- `deploy.sh v0.25.0`: 묶음 검증 → DB 백업 `db-20261002T013150Z.sqlite3` → 교체 → 스모크. `.env.django` 전후 동일.
  컨테이너 로그 "cron scripts: installed into /cron-scripts (v0.25.0 …)", `scripts/` 에 다섯 파일(UID 10001).
- crontab 에 `10 17 * * * /srv/earththrutime3d/scripts/present.sh >> …/logs/present.log 2>&1` 를 더했다.
- 첫 받기를 손으로: venv 만들기 15 초(297 MB), 받은 시각 2026-10-01 12 UTC, `status.json` ok. 컨테이너에서
  `/present-live` 가 읽힌다. 이 시각은 판의 18 UTC 보다 오래되어 `/healthz` `present.source = release` 그대로다 —
  그날 17:10 UTC 에 2026-10-02 12 UTC 를 받으면 `live` 로 바뀐다.
- 공개 사이트 `tests/flux-browser.mjs` 통과. 정리: `prune.sh` 로 v0.24.1 을 지웠다(+921 MiB, 32 GiB 여유).
- 롤백: `bash /srv/earththrutime3d/deploy.sh v0.24.2`. compose 의 새 마운트는 남지만 v0.24.2 는 읽지 않는다.
