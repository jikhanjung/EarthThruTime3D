# v0.22.0 — 이퀄 어스 투영 릴리스

상태: 2026-09-24 운영 배포·공개 Chromium 검증 완료.

## 변경

PR #86을 배포한다. 툴바 **투영** 선택에 이퀄 어스(Šavrič, Patterson & Jenny 2018)가 생겼다.
몰바이데와 같은 정적도 도법이라 면적은 같고, 극이 점이 아니라 적도 폭 59 %의 선이어서
고위도 대륙이 덜 눌린다(60°에서 지도 폭 75 % 대 65 %, 75°에서 65 % 대 42 %, 180°·적도의
최대 각변형 17° 대 50°). 시트 비율은 2.055:1이라 평면 메시가 2:1이 아닌 유일한 도법이다.
셰이더는 논문의 다항식을 θ에 대한 Newton 8회로 되돌린다. 격자·지명·판 경계·해안선·위치
핀은 기존 배치 경로를 그대로 쓴다.

자료와 셰이더의 표본 추출은 바뀌지 않으므로 묶음은 v0.21.0과 같고 코드만 바뀐다. 정적
캐시 키는 0.22.0으로 오른다. DB 스키마·seed 변경 없음.

## 빌드·운영 배포

- PR #86(구현), #87(릴리스)을 병합한 깨끗한 main `4f34c73`에서 개발 호스트 m710q가
  `build.sh v0.22.0`으로 빌드했다. Django 83개, 패킹, 이미지 스모크 통과.
- 자료 **1,288개, 482,280,982 bytes** — v0.21.0 매니페스트와 경로·크기·SHA-256이 모두 같다.
  호스트 묶음도 같다.
- 이미지 `honestjung/earththrutime3d:v0.22.0`을 Docker Hub에 push하고 dolfinid-2에서
  digest로 pull했다. 자료·호스트 아카이브는 scp 후 SHA-256을 대조했다.
- 이미지 digest: `sha256:55c1fc16cd0b5ab7d9706166847fc73c1d2fb1160a7c8cb9dc1942b2dcafc1a0`.
- 배포 전 dolfinid-2: v0.21.0 healthy, 디스크 여유 34 GB.
- 기존 `deploy.sh v0.22.0`이 자료 1,288개 검증 → DB 백업 → 컨테이너 교체 → 스모크를 완료했다.
- DB 백업 `db-20260923T231701Z.sqlite3`(파일명 UTC, 한국 시각 2026-09-24), 무결성 검사 통과.
  운영 DB 유지, `.env.django` 배포 전후 동일. 컨테이너 healthy.
- 공개 `/healthz`: `ok`, `0.22.0`, DB·스키마 정상, PaleoAtlas 필수 90개·누락 0.
  공개 HTML `globe.js?v=0.22.0`, 투영 선택에 "이퀄 어스"/"Equal Earth".
- 공개 Chromium: 이퀄 어스·몰바이데·정거원통 전환, 경선 자동 회전, 위치 핀 읽기 확인
  (콘솔·네트워크 오류 없음). `tests/pin-browser.mjs`, `tests/climate-browser.mjs`,
  13만 년 창 집중 검사 통과. 스크린숏 `data/screenshots/public-0220-{equalearth,mollweide,equirect}.png`.
- `tests/globe-browser.mjs` 전체는 종전과 같이 공개 배포의 원본 지도 비공개 설정에서
  `#surface` 토글 단계에서 멈춘다(v0.19.0·v0.20.0과 같은 알려진 제약). 개발 호스트에서는
  이퀄 어스 assertion을 포함해 전부 통과했다. Firefox BiDi는 실행하지 않았다.
- 운영: https://earththrutime.nopeoplestime.info/
- 롤백: `bash /srv/earththrutime3d/deploy.sh v0.21.0` (DB 복원 없음). v0.20.0도 남아 있다.

### 릴리스 묶음 SHA-256

```text
8ff5b0463c66c115a5182b1c47f5c3f8d01456e8867be41c9ed317ca28753647  earththrutime3d-image-v0.22.0.tar.gz
8212c603bde45e29802461d6d7c31b2bc87cadee865d2bafaea954c9b8aaadde  earththrutime3d-data-v0.22.0.tar.gz
c459ab2d2c8759e87c33aa61e1c81f53ce62b941706dcdb9c0c94118828e5563  earththrutime3d-host-v0.22.0.tar.gz
```
