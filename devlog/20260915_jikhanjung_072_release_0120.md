# jikhanjung 072 — v0.12.0 맨틀 통합 릴리스

날짜: 2026-09-15 · 상태: 운영 배포 완료

## 릴리스 범위

[070](20260915_jikhanjung_070_globe_mantle_overlay.md)과
[071](20260915_jikhanjung_071_globe_mantle_time_section.md)의 메인 지구본 맨틀 통합을 배포한다.
전 지구 Slabs/Piles와 핵 참고 구, 조절 가능한 지표 절개·불투명도, 80·60·40·20·0 Ma
시간 전환과 원본 OPT1 A–A′ 단면 팝업 연결을 포함한다. PaleoCoastlines 높이도 보정한다.
근사 좌표 정합과 참고용 핵 표시이며 새 대류·지각 변형 계산은 아니다.

## 배포 준비

- 최신 main과 열린 PR·이슈 확인: 새로운 main 커밋과 열린 PR 없음.
  하천 #30, 강수 #6 이슈와 작업 범위가 겹치지 않는다.
- 버전을 0.12.0으로 올리고 앱·이미지·배포 매니페스트 버전을 맞춘다.
- 기능 검증: Django 63개, 좌표 수치 검사, 맨틀 통합·기존 지구본·독립 단면 브라우저 통과.
- 개발 호스트 m710q에서 빌드하고 dolfinid-2의 기존 서비스에 이미지·자료 쌍을 배포한다.
  기존 운영은 v0.11.0 healthy, 사전 점검의 디스크 여유는 9.6 GB다.
- DB migration·seed 변화 없음. 새 원본 자료 다운로드 없음.
  기존 배포 절차로 자료 해시를 확인하고 DB 스냅샷·무결성 검사 후 교체한다.
  운영 DB와 비밀 설정은 보존하고 v0.11.0은 롤백용으로 남긴다.

## 배포 결과

- 기능 PR [#36](https://github.com/jikhanjung/EarthThruTime3D/pull/36) 병합 완료.
  빌드 소스와 병합 커밋은 `289c3ca`이며 작업 트리가 깨끗한 상태에서 빌드했다.
- `make check`, Django 63개 및 배포 컨테이너 스모크 통과.
- 운영 묶음: 926개 파일, 384,445,753 bytes. 전송 후 세 아카이브 체크섬과
  이미지·자료 쌍의 파일 해시 검증을 모두 통과했다. 기존 51시점 맨틀과 5시점 지역 자료를 재사용했다.
- 이미지 `honestjung/earththrutime3d:v0.12.0`:
  `sha256:a69c79d7e0d97785eebb1eaa149cb062f77f0a892d5bee03b14ce9864af5850a`.
  개발 호스트에서 빌드한 아카이브를 전송해 운영에서는 load·교체만 수행했다.
- 사전 DB 스냅샷 `db-20260915T111557Z.sqlite3`(131,072 bytes), 무결성 검사 통과.
  `.env.django`는 배포 전후 해시가 같음을 확인했다. 기존 DB를 유지했다.
- 컨테이너 healthy, 호스트 스모크 및 공개 HTTPS `/healthz` 모두 통과:
  `status=ok`, `version=0.12.0`, 기본 PaleoAtlas 90개, 필수 필드 누락 0.
- 공개 Playwright 검사 통과: 다섯 시점, 절개·불투명도·핵 토글, A–A′ 양방향 시간
  동기화, 실패/재시도, 빠른 시점 변경, 요청 취소, 투영 복원, 모바일·영문.
  기본 화면의 맨틀 요청 0건과 선택한 시점의 두 메시 요청도 확인했다.

아카이브 SHA-256:

| 파일 | SHA-256 |
|---|---|
| image-v0.12.0.tar.gz | `e4482d6f3d2dc16fede65a6c1e13e14f6e280b40147323f4ea1daeda99b9e35c` |
| data-v0.12.0.tar.gz | `6136d54952a20de00060c73d99f26ac6114530d85dcbc13305a375b5fef2ad9e` |
| host-v0.12.0.tar.gz | `7221b5a2b9123b3ad8dbcb59381800c33bca93d196318d53fdfaabb01424d6ac` |

운영 화면: [지구본](https://earththrutime.nopeoplestime.info/).
정보 패널에서 맨틀 근사 중첩을 켠다. 롤백 명령은 운영 호스트에서
`bash /srv/earththrutime3d/deploy.sh v0.11.0`이며 DB를 되돌리지 않는다.
