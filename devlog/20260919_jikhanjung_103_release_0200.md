# v0.20.0 — 시간 창의 모형 식생·강수 릴리스

상태: 2026-09-19 운영 배포·공개 Chromium 검증 완료.

## 변경

PR #75(WWolf, 이슈 #6)를 배포한다. 두 시간 창의 모든 시점에 Krapp et al. (2021)의 0.5°
모형 기후를 얹는다: BIOME4 생물군계를 식피 순으로 묶은 "모형 식생"과 연 강수량 "모형 강수".
복원이 아니라 HadCM3 통계 에뮬레이터의 결과이며, 아프리카 습윤기의 녹색 사하라를 재현하지
못한다는 점을 한영 안내가 밝힌다(wwolf 013). 검토와 두 가지 수정(부분 빌드에서 가장
오래된 stop이 relief로 떨어지던 것, 주석의 잘못된 토큰)은 PR #75 코멘트에 있다.
P08 계획 문서(#76)도 함께 병합됐다. DB 스키마와 seed는 바꾸지 않는다.

자료는 v0.19.0 대비 `paleodem-0000-climate-0…130.png` 131장(720×360, 11 MB)이 는다.
원본 `sources/quaternary-climate.json`의 SHA-256 3개를 검증한 뒤 `scripts/build_climate.py`로
생성했고, 검토 시 별도 디렉터리에 만든 결과와 바이트 단위로 같다.

## 빌드·운영 배포

- PR #75(구현+검토 수정), #76(P08 계획), #77(릴리스)을 병합한 깨끗한 main `e965d14`에서
  개발 호스트 m710q가 `build.sh v0.20.0`으로 빌드했다. Django 83개, 패킹, 이미지 스모크 통과.
- 자료 **1,288개, 482,280,982 bytes**. v0.19.0 매니페스트와 비교해 새 파일 131개(모두
  `climate-*.png`), 변경·삭제 0개. 호스트 묶음은 v0.18.1 이후 해시가 같다.
- 이미지 `honestjung/earththrutime3d:v0.20.0`을 Docker Hub에 push하고 dolfinid-2에서
  digest로 pull했다. 자료·호스트 아카이브는 scp 후 SHA-256을 대조했다.
- 이미지 digest: `sha256:da5086b33e5f74e4493f5d0ed31ecdd560cd994457f95c696892a65832cd5a9a`.
- 배포 전 dolfinid-2: v0.19.0 healthy, 디스크 여유 15 GB(자료 추출 후 14 GB).
- 기존 `deploy.sh v0.20.0`이 자료 1,288개 검증 → DB 백업 → 컨테이너 교체 → 스모크를 완료했다.
- DB 백업 `db-20260919T035804Z.sqlite3`, 131,072 bytes, 무결성 검사 통과(파일명 UTC).
  운영 DB 유지, `.env.django` 배포 전후 동일. 컨테이너 healthy.
- 공개 `/healthz`: `ok`, `0.20.0`, DB·스키마 정상, PaleoAtlas 필수 90개·누락 0.
- 공개 기후 PNG 5장(0·8·21·80·130 ka)을 내려받아 빌드 묶음과 SHA-256 일치를 확인했다.
  13만 년 창 HTML에 토글 2개·안내·`globe.js?v=0.20.0`·기후 URL 131개가 있고, 전체
  시리즈에는 토글이 없다.
- 공개 Chromium: `tests/climate-browser.mjs`(두 모드·범례·사하라 안내·시점 전환·모바일·
  한영), `tests/river-browser.mjs`, 그리고 v0.19.0의 13만 년 창 집중 검사(21/26/40/60/
  80/100 ka의 빙상 종류·하천 나이·해수면·점선) 모두 통과, 콘솔·네트워크 오류 없음.
  스크린숏 `data/screenshots/public-0200-{veg-21ka,rain-21ka,veg-8ka}.png`.
  Firefox BiDi는 실행하지 않았다.
- 운영: https://earththrutime.nopeoplestime.info/
- 롤백: `bash /srv/earththrutime3d/deploy.sh v0.19.0` (DB 복원 없음). v0.18.x·v0.19.0은
  남아 있다(prune 미실행, 디스크 77%).

### 릴리스 묶음 SHA-256

```text
dd5ca7fa11f068d7c1c40594c1a99b0d454c80fc439c6ed4755d7a26d8f91c86  earththrutime3d-image-v0.20.0.tar.gz
cb9c781824b866ae6c30113f3f4e40b797e903713405b4a9a808c50af61fc825  earththrutime3d-data-v0.20.0.tar.gz
c459ab2d2c8759e87c33aa61e1c81f53ce62b941706dcdb9c0c94118828e5563  earththrutime3d-host-v0.20.0.tar.gz
```
