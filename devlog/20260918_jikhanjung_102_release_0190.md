# v0.19.0 — 13만 년 창의 PaleoMIST 빙상·하천 릴리스

상태: 2026-09-18 운영 배포·공개 Chromium 검증 완료.

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

## 빌드·운영 배포

- PR #71(검토), #72(구현), #73(릴리스)을 순서대로 병합한 깨끗한 main `097dc04`에서
  개발 호스트 m710q가 `build.sh v0.19.0`으로 빌드했다. Django 83개, 패킹, 이미지 스모크 통과.
- 자료 **1,157개, 471,153,936 bytes**. v0.18.1 매니페스트와 비교해 새 파일 77개(빙상 조각
  55, 빙기 하천 22), 변경 2개(`ice-sources.json`, `paleodem-0000-rivers-ice.json`),
  삭제·기타 변경 0개. 호스트 묶음은 v0.18.1과 해시가 같다.
- 이미지 `honestjung/earththrutime3d:v0.19.0`을 Docker Hub에 push하고 dolfinid-2에서
  digest로 pull했다. 자료·호스트 아카이브는 scp 후 SHA-256을 대조했다.
- 이미지 digest: `sha256:206cf263c18c769dc1fb739601e49a7c53471dde96772c6678befb44ba26a18c`.
- 배포 전 dolfinid-2: v0.18.1 healthy, 디스크 여유 14 GB(자료 추출 후 13 GB).
- 기존 `deploy.sh v0.19.0`이 자료 1,157개 검증 → DB 백업 → 컨테이너 교체 → 스모크를 완료했다.
- DB 백업 `db-20260918T142003Z.sqlite3`, 131,072 bytes, 무결성 검사 통과(파일명 UTC).
  운영 DB 유지, `.env.django` 배포 전후 동일. 컨테이너 healthy.
- 공개 `/healthz`: `ok`, `0.19.0`, DB·스키마 정상, PaleoAtlas 필수 90개·누락 0.
- 공개 새 PNG 8장(빙상 26·40·60·80 ka, 하천 27.5·40·60·80 ka)을 내려받아 빌드 묶음과
  SHA-256 일치를 확인했다. 공개 HTML에 `globe.js?v=0.19.0`, 모델 안내, reconstructed 프레임
  55개, `sealevel.model` 곡선이 있다.
- 공개 Chromium, `?window=lastcycle`: 21 ka drawn·하천 21.0, 26/40/60/80 ka
  reconstructed·모델 안내·하천 나이 일치·캡션 "모델 복원 빙상", 100 ka analogue·가정 안내,
  해수면이 각 프레임 값이며 슬라이더 잠김, 색띠 `.sea-model` 점선, 영어 캡션 "modelled ice".
  콘솔·네트워크 오류 없음. 스크린숏 `data/screenshots/public-0190-cycle-40ka.png`
  (40 ka에 허드슨만 열림). `tests/river-browser.mjs`도 공개 사이트에서 통과했다.
  `tests/globe-browser.mjs` 전체는 종전과 같이 공개 사이트의 원본 지도 비공개 설정에서
  `#surface` 토글 단계에서 멈추므로 위 집중 검사로 대신했다. Firefox BiDi는 실행하지 않았다.
- 운영: https://earththrutime.nopeoplestime.info/
- 롤백: `bash /srv/earththrutime3d/deploy.sh v0.18.1` (DB 복원 없음). v0.18.0/0.18.1은 남아 있다.

### 릴리스 묶음 SHA-256

```text
8304fe4c8e3e19e6fd87d2046cc0e39f03a52f541f01e97359dfdea5fd406f23  earththrutime3d-image-v0.19.0.tar.gz
d56fbc8c7b51a1b2c0b8e51ec1f07703986ff5ca7d55cb601be52d07b264b56b  earththrutime3d-data-v0.19.0.tar.gz
c459ab2d2c8759e87c33aa61e1c81f53ce62b941706dcdb9c0c94118828e5563  earththrutime3d-host-v0.19.0.tar.gz
```
