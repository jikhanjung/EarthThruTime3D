# v0.16.0 — CRUST 2.0 지각 표시 릴리스

상태: 2026-09-16 운영 배포·공개 Chromium/Firefox 검증 완료.

## 구현·병합과 빌드

- [PR #60](https://github.com/jikhanjung/EarthThruTime3D/pull/60): head `6da0e25`,
  merge `4de002e`. 깨끗한 main `4de002e`에서 v0.16.0을 빌드했다.
- 구현·자료 검증은 [091](20260916_jikhanjung_091_crust2_visualization.md),
  범위와 해석은 [지각 문서](../docs/crust.md)에 기록했다.
- 현재(0 Ma) 지각 두께 색상·km 읽기·절개층·1×/5× 표시를 제공한다.
  과거 연대에서는 숨기고 현재로 돌아오면 캐시를 재사용한다. 맨틀 절개와도 연결한다.
- 2° 모형을 재표본화한 표시 자료이며, 화면의 세밀함이 원자료 해상도를 높이지 않는다.
  물·얼음 포함과 고도 기준이 미확정이므로 절개층은 표시 지표 아래 두께 등가층이다.
  실제 모호면 깊이나 과거 지각 변형 계산으로 해석하지 않는다.
- `make check`, `make test` 통과: Django 83개, JS 29개(7개 파일).
  이미지 빌드 및 지각 자료를 포함한 컨테이너 스모크도 통과했다.
- 자료 **1,080개, 445,725,507 bytes**. v0.15.1의 1,077개는 경로·크기·SHA-256이
  모두 동일하고, 지각 카탈로그·바이너리·gzip 3개(196,120 bytes)만 추가했다.
  지각 바이너리 129,600 bytes, gzip 전송 65,829 bytes. DB 스키마·seed 변경 없음.

## 운영 배포와 검증

- 개발 호스트에서 이미지 `honestjung/earththrutime3d:v0.16.0`을 빌드·push했다.
  dolfinid는 아래 digest로 이미지를 pull했고, 자료·호스트 묶음은 전송 후 SHA-256을 대조했다.
- 이미지 digest: `sha256:b2a5b2e4b2fcb3be266cc98270ec3025e56c6686c3707101868fafa07be2530d`.
- 새 버전 자료 디렉터리의 1,080개 파일을 검증한 뒤 기존 `deploy.sh v0.16.0`으로
  DB 백업 → 컨테이너 교체 → 상태 확인·스모크를 수행했다. 운영 서버에서 빌드하지 않았다.
- DB 스냅샷 `db-20260916T144724Z.sqlite3`, 131,072 bytes, 무결성 검사 통과.
  운영 DB 유지, `.env.django` 배포 전후 동일. 배포 전 디스크 여유 13 GB.
- 공개 `/healthz`: `ok`, `0.16.0`, DB·스키마 정상, PaleoAtlas 필수 90개·누락 0.
- 공개 Chromium: 지연 로딩·재시도·캐시, 연대 전환과 늦은 응답 차단, 평면 투영,
  극·날짜변경선 절개, 맨틀 절개 공유, 모바일 화면 검사 통과.
- 공개 Firefox 146.0.1: 지각 색상·절개·5×·20→0 Ma, 기본 지구본·하천,
  −60 m의 12.7 ka 구간 및 20 ka 빙하/하천 검사 통과. 콘솔·네트워크 오류 없음.
- 운영: https://earththrutime.nopeoplestime.info/
- 롤백: `bash /srv/earththrutime3d/deploy.sh v0.15.1` (DB 복원 없음).

| 아카이브 | SHA-256 |
|---|---|
| image-v0.16.0.tar.gz | `d3cc5f1711b5c0106e78a96f3a9d0a26cf4329d632b19686a4babb9fe0a5f457` |
| data-v0.16.0.tar.gz | `08364eca258e6bdc2327b239661ed8d0ef144e0c335bfdfa6cb4a3980e047139` |
| host-v0.16.0.tar.gz | `c459ab2d2c8759e87c33aa61e1c81f53ce62b941706dcdb9c0c94118828e5563` |

이미지 아카이브는 개발 호스트에 보관했고 운영에는 레지스트리 digest로 전달했다.

## 기록 점검

배포 README·운영 현황·P07·devlog 인덱스를 갱신했다. 배포 후 main에 추가된
`d6ecc63`의 OPT1 GPU 계획 문서는 기록 브랜치에 반영했으며 실행 코드 변경은 없다.
열린 PR #56과 이슈 #59·#6은 이번 배포에 포함하지 않았다. 문서 링크와
`git diff --check`를 확인하고 별도 기록 커밋을 push한다. 기존 작업 브랜치는 유지한다.
