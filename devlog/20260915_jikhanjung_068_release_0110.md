# jikhanjung 068 — v0.11.0: 맨틀과 인도–아시아 단면 릴리스

날짜: 2026-09-15 · 상태: 운영 배포 완료

## 릴리스 내용

[066](20260915_jikhanjung_066_mantle_source_preview.md)의 맨틀 모형 화면과
[067](20260915_jikhanjung_067_india_asia_section.md)의 A–A′ 팝업·3D 지표를 배포한다.
맨틀 51시점과 지역 5시점의 모든 파일·gzip 표현을 운영 묶음에 넣고 경로·크기·해시를
검증한다. 원본 ZIP이나 지도 이미지는 배포하지 않는다.

단면·맨틀과 3D 지표는 발표된 자료의 표시다. 지각 단축과 대류 화살표는 가정·개념도이며
실제 지각 변형·대류를 계산한 것으로 표시하지 않는다. 단면과 지역 지형 자료는 전체
gzip 420,502 bytes다. 코드 버전은 v0.11.0, Django는 5.2 계열을 유지한다.

## 배포 준비와 검증

- 최신 main과 동일한 기반을 확인했다. 진행 중인 PR은 없고, 열린 하천·강수 이슈와 겹치지 않는다.
- 데이터 패커는 맨틀 51시점·단면 5시점과 지형 필드를 요구하며, 변조된 입력을 거부한다.
- Docker 이미지에 새 runtime 경로를 지정했다. 이미지 스모크에 단면 데이터·gzip·맨틀
  파일의 실제 제공 검사를 추가했다.
- 배포 시 Compose `.env`의 추가 설정과 기존 포트를 보존하도록 했다. `.env.django`는
  변경하지 않는다. 기동뿐 아니라 healthcheck·smoke 실패도 이전 구성으로 되돌린다.
- 기존·신규 Django 검사, 수치 전처리 검사와 브라우저 검사를 수행한다. 최종 빌드·배포
  결과는 운영 확인 후 이 기록에 추가한다.

DB migration 변화나 seed는 없다. 배포 직전 백업은 기존 스냅샷 API 경로로 만들며
검증된 이미지·데이터 쌍만 교체한다. 코드 롤백은 DB를 복원하지 않는다.

## 최종 결과

- 기능 PR [#33](https://github.com/jikhanjung/EarthThruTime3D/pull/33)을 main에 병합했다.
  빌드 소스는 `3cda804`, 병합 커밋은 `17b2d3a`다.
- `make check`, Django 61개 테스트, 전처리·수치 검사와 Docker 컨테이너 스모크가 통과했다.
  운영 묶음은 926개 파일, 384,445,753 bytes이며 전송 후 SHA-256을 다시 검증했다.
- 개발 호스트에서 빌드한 `honestjung/earththrutime3d:v0.11.0`을 아카이브로 전송해
  dolfinid에서 load·교체했다. 운영 이미지 ID는
  `sha256:89f5bd0aa0a1a1e1e13e369b61085c9e8f7369beeed4333ba9debcba20b634d1`이다.
- 배포 직전 `db-20260915T082043Z.sqlite3`(131,072 bytes)를 생성하고 무결성을 확인했다.
  기존 운영 비밀 설정과 DB를 유지했다. 이전 v0.10.5 이미지·자료는 롤백용으로 보존했다.
- 공개 HTTPS `/healthz`: `status=ok`, `version=0.11.0`, 기본 PaleoAtlas 필드 90개,
  누락 0. 컨테이너 healthy와 호스트 스모크도 통과했다.
- 공개 사이트에서 Playwright로 A–A′ 팝업의 지연 로딩, 80→0 Ma 전환, 3D 지표,
  수직 배율, 지각 가정 조절, 재생, Escape·포커스 복원, 모바일·영문 화면을 검증했다.
- 맨틀 화면도 공개 주소에서 gzip 전송, 시점 전환, 연속 입력 취소, 레이어 토글,
  브라우저 내 요청 실패 모의·복구, 모바일·영문 표시를 확인했다. 페이지 오류는 없었다.

운영 화면: [지구본](https://earththrutime.nopeoplestime.info/),
[인도–아시아 단면](https://earththrutime.nopeoplestime.info/collision/),
[맨틀 모형](https://earththrutime.nopeoplestime.info/mantle/).
