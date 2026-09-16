# v0.15.0 — 호수 표시와 자료 빌드·Firefox 검사 보완

상태: 2026-09-16 운영 배포·공개 Firefox 검증 완료.

## 병합과 릴리스 범위

- [#47](https://github.com/jikhanjung/EarthThruTime3D/pull/47) Firefox BiDi 검사 보완:
  head `9eaf730`, merge `6f8ea9a`.
- [#48](https://github.com/jikhanjung/EarthThruTime3D/pull/48) 호수 채널·RGB 형식·캐시 보완:
  작성자의 갱신된 `e1fc0d3`를 반영했고 최종 head `bbe5e9e`, merge `985e8ee`.
- [#53](https://github.com/jikhanjung/EarthThruTime3D/pull/53) 고정 OPT1 빌드 입력에서 가변 API
  메타데이터 분리: head `911ad61`, merge `18f4840`. Issue #50은 닫혔다.
- 상세 구현·검증은 jikhanjung 083–085. 앱·Docker·배포 버전 모두 0.15.0.
- 빌드 소스는 깨끗한 main `985e8ee`. 마이그레이션·seed 변경 없음.

## 자료 생성과 검증

- 일반 109장·저수위 31장을 RGB로 변환했다. 원래 red 바이트는 전부 일치하고 G/B는 0이다.
- 검증된 PaleoMIST 입력으로 빙기 10장(2.5–25 ka, 2.5 ka 간격)을 다시 생성했다.
  배포 시리즈는 10장이며 PR 작성자의 다른 환경에서 만든 32장과 구분한다.
- 하천 PNG 150장 합계 61,082,334 bytes. 이전 L 자료는 `.build/river-before-rgb`에 보관했다.
- 호수는 계산된 웅덩이와 50% 중첩 규칙에 따른 근사 결과다. 실제 호수의 검증된 복원이 아니다.
  일반·저수위의 호수 채널은 0이며, 현재 0 m 지표로 저장된 카스피해의 기존 한계도 유지된다.
- 전체 자료 묶음: **1,077개 파일, 445,529,387 bytes**. 운영 전송 후 모든 파일 검증 통과.
- `make check`, `make test` Django 77개, `npm test` 6개 파일, 하천 검사 12개 통과.
  이미지 빌드의 Django·마이그레이션 누락 검사와 컨테이너 스모크도 통과했다.
- 로컬 Firefox: PNG·셰이더·토글·안내·모바일·한영·저수위·시간 창 검사 통과.

## 운영 배포 결과

- 배포 전 v0.14.1 healthy, 디스크 여유 15 GB. 아카이브를 dolfinid로 전송하고
  SHA-256 대조 → 이미지 load → 버전별 자료 추출 → 기존 `deploy.sh v0.15.0` 순서로 배포했다.
- 이미지: `sha256:bfbeddf5264f18887f01d19261b39f1988aef2be0a6b8414236ff95800c41571`.
- DB 스냅샷 `db-20260916T041611Z.sqlite3`, 131,072 bytes, 무결성 검사 통과.
  운영 DB 유지, `.env.django` 배포 전후 해시 일치. 컨테이너 healthy.
- 상태 응답: `ok`, 버전 `0.15.0`, DB·스키마 정상, PaleoAtlas 필수 90개·누락 0.
- 공개 Firefox BiDi: 지구본·하천, −60 m의 12.7 ka 빙기 구간, 20 ka 빙하·하천,
  콘솔·네트워크 오류 없음 확인.
- 공개 Firefox 추가 검사: 빙기 PNG 10개 응답, −20/−60/−100/−130 m 구간,
  현재 복귀, 21 ka·70 ka 시간 창 통과.
- 공개 맨틀: 기본 절개 Off·불투명도 70%, 실제 렌더 값 false/0.7 확인.
  중첩을 끄면 지표 불투명도 1로 복원하며 페이지 오류 없음.
  기존 기본값 검사 스크립트의 출력 문구는 v0.14.1이지만 실행 대상은 이번 배포의 공개 주소였다.
- 운영: https://earththrutime.nopeoplestime.info/
- 롤백: `bash /srv/earththrutime3d/deploy.sh v0.14.1` (DB 복원 없음).

| 아카이브 | SHA-256 |
|---|---|
| image-v0.15.0.tar.gz | `37562123a261f6e36b0cb2f04b480825adf5783d8a76b40e8d09a41f5731c266` |
| data-v0.15.0.tar.gz | `8c0ceaf29e5997553c9b5e25a1bdd2f6a0cabb931f2d6543c8a6c0dd47317be4` |
| host-v0.15.0.tar.gz | `c459ab2d2c8759e87c33aa61e1c81f53ce62b941706dcdb9c0c94118828e5563` |

배포 완료 후 P06 및 기록 누락 점검은 [087](20260916_jikhanjung_087_p06_deployed_review.md)에 이어 기록한다.
