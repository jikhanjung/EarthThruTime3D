# v0.17.0 — 현재 하천·호수 자료 릴리스

상태: 2026-09-17 운영 배포·공개 Chromium/Firefox 검증 완료.

## 검토·병합

- [PR #56](https://github.com/jikhanjung/EarthThruTime3D/pull/56), 검토 head `cbd9594`,
  merge `5594218`. 기존 경로 탐색·호수 섬 처리·캐시 검증의 세 결함이 수정됐다.
- `make check`, Django 83개, present-water 12개, rivers 12개, JS 7개 파일 검사 통과.
  병합 전 Chromium·Firefox UI 검사는 기존 파생 자료로 실행했다.
- Natural Earth 하천 중심선과 HydroLAKES 원본을 manifest SHA-256으로 검증했다.
  HydroLAKES는 검증된 추출 파일과 receipt를 남기고 다운로드 ZIP은 fetcher가 삭제했다.
- 배포 대상은 현재 격자 2장과 2.5–25 ka 빙기 10장이다. `--ice --ice-to 25`로 재생성하고
  파일 목록·sidecar·최종 묶음을 확인한다. #59의 26–80 ka 확대는 포함하지 않는다.
- 실제 자료 재생성 후 브라우저 검사와 호수 채널·주요 지역 확인을 수행한다.
  버전은 앱·Docker·배포 설정 모두 0.17.0으로 갱신한다.

## 자료 해석과 운영 범위

현재의 강줄기는 낮은 해상도 지형에서 막힌 협곡을 보완하는 라우팅 가이드다.
표시하는 하천은 계산된 잠재 배수망이며, 과거의 관측 하천 복원이 아니다.
빙기 시점의 얼음 밖에는 현재 호수 윤곽을 사용하는 근사가 포함된다.
세부 알고리즘과 알려진 유역 한계는 wwolf 011·012 및 `docs/globe-viewer.md`를 따른다.

배포 전 dolfinid-2는 v0.16.0 healthy, 필수 자료 누락 0, 디스크 여유 12 GB였다.
개발 호스트 m710q에서 이미지를 빌드하고 레지스트리를 통해 운영에 전달한다.
운영 DB·비밀 설정을 유지하며 기존 배포 스크립트의 백업·상태 확인 절차를 사용한다.
기존 브랜치는 삭제하지 않는다.

## 재생성·실제 자료 검증

- 캐시: 강 41,741, 호수 19,174, 폐쇄 호수 1,622 texels로 작성자 결과와 일치했다.
  강줄기 2,265개, 분수계 접촉 제거 1,151 texels, 연결 보완 46개, 하구 확장 92개.
- 0 m 라우팅을 별도로 계산해 도나우 삼각주 0.810, 철문 0.612, 아마존 5.746 Mkm²를
  확인했다(지정 좌표 주변 7×7셀 최대 집수 면적). 볼가는 최초 표본 위치가 출구 제거 셀에
  해당해 0을 반환했으므로 PR의 볼가 유역 수치를 독립 확인했다고 주장하지 않는다.
- 캐시에서 매니툴린 서부·중앙 표본은 호수 깊이 0, 휴런호 표본은 59.8 m였다.
  카스피해 표본은 200.5 m와 폐쇄 호수 표시를 확인했다. 섬 안의 작은 호수도 있으므로
  섬 전체의 모든 셀이 항상 0이어야 하는 것은 아니다.
- 현재·저수위·10 ka·25 ka PNG의 RGB 형식, 호수 green 채널과 blue=0을 확인했다.
  sidecar 시점은 2.5, 5, …, 25 ka이며 실제 빙기 PNG도 정확히 10장이다.
- 새 자료로 로컬 Chromium 하천 검사, Firefox 하천·−60 m·20 ka 및 지각 검사를 통과했다.
  검사 스크린샷은 gitignored `test-results/`에 저장했다. 별도 지역 도표 생성은
  matplotlib 미설치로 실행하지 못했고, 이를 시각 검증 결과에 포함하지 않았다.

## 빌드·운영 배포

- 릴리스 PR [#62](https://github.com/jikhanjung/EarthThruTime3D/pull/62)를 병합한
  깨끗한 main `35f01a4`에서 개발 호스트 m710q가 빌드했다. 이미지 컨테이너 스모크 통과.
- 자료 **1,080개, 445,775,830 bytes**. v0.16.0과 경로 목록이 같고 현재 2장·빙기 10장
  PNG만 변경됐다. 나머지 1,068개는 SHA-256이 같다. DB 스키마·seed 변경 없음.
- 이미지 `honestjung/earththrutime3d:v0.17.0`을 Docker Hub에 push하고 dolfinid에서
  digest로 pull했다. 자료·호스트 아카이브는 전송 후 SHA-256을 대조했다.
- 이미지 digest: `sha256:680dc5c604da5e7d7a8b71818a3c30ad325a47f448c11c7655db864fcb0ef673`.
- 기존 `deploy.sh v0.17.0`이 자료 1,080개 검증 → DB 백업 → 컨테이너 교체 → 스모크를 완료했다.
- DB 백업 `db-20260917T053451Z.sqlite3`, 131,072 bytes, 무결성 검사 통과.
  운영 DB 유지, `.env.django` 배포 전후 동일. 컨테이너 healthy.
- 공개 `/healthz`: `ok`, `0.17.0`, DB·스키마 정상, PaleoAtlas 필수 90개·누락 0.
- 공개 새 PNG 12개를 직접 내려받아 빌드 묶음과 SHA-256 일치를 확인했다.
- 공개 Chromium: 하천 PNG·shader·toggle·저수위·시간 창·모바일·한영 검사 통과.
  공개 Firefox 146.0.1: 하천·−60 m의 12.7 ka 구간·20 ka 및 지각 색상·절개·5×·20→0 Ma
  검사 통과. 검사에서 콘솔·네트워크 오류 없음.
- 운영: https://earththrutime.nopeoplestime.info/
- 롤백: `bash /srv/earththrutime3d/deploy.sh v0.16.0` (DB 복원 없음).

| 아카이브 | SHA-256 |
|---|---|
| image-v0.17.0.tar.gz | `76d33423d32446bbf912520320262a6738311f733ae303cfb3fa68862eabcd00` |
| data-v0.17.0.tar.gz | `c926de97841b32e258b1c0e09eb42c59870541471a193d36327d25e47b5c90b2` |
| host-v0.17.0.tar.gz | `c459ab2d2c8759e87c33aa61e1c81f53ce62b941706dcdb9c0c94118828e5563` |

이미지 아카이브는 개발 호스트에 보관했다. 운영 안내·devlog 인덱스와 이 배포 결과를
별도 문서 커밋으로 commit/push한다. 기존 작업 브랜치는 유지한다.
