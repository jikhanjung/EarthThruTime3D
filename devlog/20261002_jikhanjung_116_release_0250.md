# v0.25.0 — 현재의 바람·구름 하루 한 번 받기 릴리스

상태: 릴리스 준비. 빌드·운영 배포 결과는 아래에 이어 적는다.

## 변경

- [#108](https://github.com/jikhanjung/EarthThruTime3D/pull/108) 호스트 cron 이 매일 17:10 UTC 에 그날 12 UTC 분석을
  `present-live/` 에 받고, 앱이 새것이면 쓴다([jikhanjung P11](20261002_jikhanjung_P11_daily_present_weather.md)·
  [115](20261002_jikhanjung_115_daily_present_weather.md)). 자료 묶음은 v0.24.0 과 같다. **호스트 묶음이 바뀐다**
  (compose 마운트, `deploy.sh`, `crontab.earththrutime3d`) — 처음 한 번 할 일은 `deploy/README.md`.
