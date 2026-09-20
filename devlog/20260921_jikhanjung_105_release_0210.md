# v0.21.0 — 위치 핀 릴리스

상태: 2026-09-21 운영 배포·공개 Chromium 검증 완료.

## 변경

PR #80(WWolf, wwolf P01·014·015)을 배포한다. ☰ 메뉴의 **위치 핀**: 지도를 눌러 놓은 현재의
장소(최대 3개)를 PALEOMAP 2016 회전 모델로 시간축을 따라 옮기고, 정보 패널에 오늘·지금의
좌표, 판, 쌍별 대원 거리를 적으며 주소(`pin=`)로 공유한다. 계산이지 관측이 아니며, 모델 간
차이·강체 판·2002 지도 300 Ma 이전 제외·도달 한계를 화면이 밝힌다. 검토에서 찾은 세 결함
(평면 지도 자동 회전 중 패널 버튼 불능, 모델 fetch 실패 시 예외, 2002 지도의 무반응 클릭)은
`eda87be`로 고쳐 함께 병합했다. 자료 묶음은 v0.20.0과 같고 코드만 바뀐다. 정적 캐시 키는
0.21.0으로 오른다. CHANGELOG의 "다음 릴리스" 항목을 v0.21.0으로 확정했다.

## 빌드·운영 배포

- PR #80(구현+검토 수정), #83(릴리스)을 병합한 깨끗한 main `510f68b`에서 개발 호스트
  m710q가 `build.sh v0.21.0`으로 빌드했다. Django 83개, 패킹, 이미지 스모크 통과.
- 자료 **1,288개, 482,280,982 bytes** — v0.20.0 매니페스트와 경로·크기·SHA-256이 모두 같다.
  호스트 묶음도 같다.
- 이미지 `honestjung/earththrutime3d:v0.21.0`을 Docker Hub에 push하고 dolfinid-2에서
  digest로 pull했다. 자료·호스트 아카이브는 scp 후 SHA-256을 대조했다.
- 이미지 digest: `sha256:48e75234be6493a21db289e3f1f9045c43ead4ec768efcb82d13b6d6eb6f1161`.
- 배포 전 dolfinid-2: v0.20.0 healthy. 루트 파일시스템이 58 GB에서 77 GB로 늘어나 있었고
  여유 30 GB였다(이 프로젝트 밖의 변경).
- 기존 `deploy.sh v0.21.0`이 자료 1,288개 검증 → DB 백업 → 컨테이너 교체 → 스모크를 완료했다.
- DB 백업 `db-20260920T235303Z.sqlite3`, 131,072 bytes, 무결성 검사 통과(파일명 UTC, 한국
  시각 2026-09-21). 운영 DB 유지, `.env.django` 배포 전후 동일. 컨테이너 healthy.
- 공개 `/healthz`: `ok`, `0.21.0`, DB·스키마 정상, PaleoAtlas 필수 90개·누락 0.
  공개 HTML `globe.js?v=0.21.0`.
- 공개 Chromium: `tests/pin-browser.mjs`(클릭/드래그 구분, 주소의 핀, "지금"·×, 스위치,
  사라진 땅, 2002 지도, 평면 지도, 시간 창, 한영) 통과. 13만 년 창 집중 검사 통과.
  `?masks=paleodem2018&age=200&pin=126.98,37.57;-87.63,41.88;2.35,48.86`에서 핀 3개,
  서울 "판 604 · 지금 46.2°N 133.9°E", 시카고–파리 3,940 km(오늘 6,650 km). 콘솔·네트워크
  오류 없음. 스크린숏 `data/screenshots/public-0210-pins-200ma.png`. Firefox BiDi는 실행하지 않았다.
- 운영: https://earththrutime.nopeoplestime.info/
- 롤백: `bash /srv/earththrutime3d/deploy.sh v0.20.0` (DB 복원 없음). v0.19.0도 남아 있다.

### 릴리스 묶음 SHA-256

```text
53d1113ee3291f199f27d2359be2872ebb66a86d4831e5f9b49044b4bc8c4f8b  earththrutime3d-image-v0.21.0.tar.gz
27598e29f8f81de650bd38cf712a00416174892d42d954c16f26911b109df84d  earththrutime3d-data-v0.21.0.tar.gz
c459ab2d2c8759e87c33aa61e1c81f53ce62b941706dcdb9c0c94118828e5563  earththrutime3d-host-v0.21.0.tar.gz
```
