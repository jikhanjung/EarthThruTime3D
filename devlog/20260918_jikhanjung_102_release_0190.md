# v0.19.0 — 13만 년 창의 PaleoMIST 빙상·하천 릴리스

상태: 배포 준비 중.

## 변경

PR #72(이슈 #59 (b) 단계)를 배포한다. 13만 년 창의 26–80 ka 빙상이 유사 자료에서
PaleoMIST 1.0의 접지 빙상으로 바뀌고, 창의 하천은 나이 기준으로 2.5–80 ka 32장의 빙기
필드를 고른다. 해수면은 스택을 유지하며 PaleoMIST 자체 곡선을 색띠에 점선으로 겹친다.
검토 근거는 [100](20260918_jikhanjung_100_glacial_window_paleomist_review.md),
구현·검증은 [101](20260918_jikhanjung_101_paleomist_window_ice.md)에 있다.
DB 스키마와 seed는 바꾸지 않는다.

자료는 v0.18.1 대비 빙상 조각 55장(26–80 ka, 약 15 MB)과 빙기 하천 필드 22장
(27.5–80 ka, 약 9 MB)이 늘고, sidecar `ice-sources.json`·`paleodem-0000-rivers-ice.json`이
바뀐다. 1–25 ka 조각과 2.5–25 ka 하천 필드는 바이트 단위로 같다.

## 절차

운영 DB와 `.env.django`를 유지하고 기존 deploy.sh의 자료 검증 → DB 백업 → 교체 →
스모크를 그대로 쓴다. 개발 호스트 m710q에서 빌드해 Docker Hub와 scp로 전달한다.
