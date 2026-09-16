# v0.15.1 — 맨틀 JS 모듈 분리 릴리스

상태: 2026-09-16 운영 배포·공개 Firefox 검증 완료.

## 구현·병합과 빌드

- [#55](https://github.com/jikhanjung/EarthThruTime3D/pull/55): `refactor/mantle-modules`,
  head `d864605`, merge `61d5568`. JS 정리·scene 분리·globe 연결 정리. 기존 브랜치는 유지했다.
- [#57](https://github.com/jikhanjung/EarthThruTime3D/pull/57): `fix/mantle-module-cache`,
  head `19f6b28`, merge `7e9d92f`. 캐시된 옛 중첩 API와 새 호출부가 섞이지 않도록 import map에 버전 지정.
- 구현·검증은 [088](20260916_jikhanjung_088_mantle_js_modules.md). 버전은 앱·Docker·배포 설정 모두 0.15.1.
- 최종 빌드 소스는 깨끗한 main `7e9d92f`. #55만 반영한 최초 준비 이미지는 배포하지 않고
  #57 병합 후 다시 빌드했다. 신규 PR #56의 현재 수계 자료 추가는 이번 릴리스에 포함되지 않았다.
- 최종 `make check`, Django 78개, JS 6개 파일 및 이미지 실행 스모크 통과.
  Chromium 전체 지구본·중첩·전환 검사와 Firefox 검증 결과는 088에 기록했다.
- 자료 **1,077개, 445,529,387 bytes**. v0.15.0과 경로·크기·SHA-256이 모두 일치한다.
  자료 재생성, 좌표계·해상도·과학 모형 변경, DB 마이그레이션·seed 변경 없음.

## 운영 배포

- 배포 전 v0.15.0 healthy, 디스크 여유 14 GB.
- 최종 아카이브를 dolfinid로 전송해 세 파일의 SHA-256을 대조했다. 이미지 load와
  버전별 자료 추출 후 기존 `deploy.sh v0.15.1`로 자료 검증 → DB 백업 → 교체 → 스모크를 수행했다.
- 이미지 `sha256:6297c5b30ac6092889163fc11ea73e4ea89b58713691ce65386ee06ef1dc25c6`.
- DB 스냅샷 `db-20260916T064722Z.sqlite3`, 131,072 bytes, 무결성 검사 통과.
  운영 DB 유지. `.env.django` 배포 전후 SHA-256 일치.
- 자료 1,077개 검증 통과, 컨테이너 healthy, 상태 응답 `ok`, `0.15.1`, DB·스키마 정상,
  PaleoAtlas 필수 90개·누락 0.
- 공개 Firefox BiDi: 기본 지구본·하천, −60 m의 12.7 ka 구간, 20 ka 빙하/하천,
  콘솔·네트워크 오류 없음 확인.
- **기존 브라우저 캐시에서의 업데이트 확인:** 배포 전에 실제 공개 v0.15.0에서 맨틀을 켜
  이전 모듈을 읽은 Firefox 컨텍스트를 유지했다. 배포 후 같은 컨텍스트로 다시 방문하여
  두 모듈의 `?v=0.15.1` import map, 절개 Off/불투명도 70%, 80→60→80 Ma,
  중첩 해제 시 불투명도 1 복원을 확인했다. 두 방문 모두 페이지 오류가 없었다.
- 운영: https://earththrutime.nopeoplestime.info/
- 롤백: `bash /srv/earththrutime3d/deploy.sh v0.15.0` (DB 복원 없음).

| 아카이브 | SHA-256 |
|---|---|
| image-v0.15.1.tar.gz | `26597281aa368049012deec9099316e0c10b5ab8b3a881d2d40727aae925c3fb` |
| data-v0.15.1.tar.gz | `594e7ac8188900eee4f092987d700f09136be2bf4b45218f68ef28ba585319ec` |
| host-v0.15.1.tar.gz | `c459ab2d2c8759e87c33aa61e1c81f53ce62b941706dcdb9c0c94118828e5563` |

## 기록 점검

088의 구현·검증, P06 후속 상태, devlog 인덱스, 배포 README와 운영 현황을 갱신했다.
수정 전 리뷰·이전 릴리스의 기록은 보존했다. 문서 링크와 `git diff --check`를 확인했으며,
배포 결과를 별도 문서 커밋으로 commit/push한다. 기존 작업 브랜치는 삭제하지 않는다.
