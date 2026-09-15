# jikhanjung 075 — v0.13.0 하천·맨틀 리뷰 수정 릴리스

날짜: 2026-09-16 · 상태: 운영 배포·공개 검증 완료

## 범위와 기록 확인

- #38 import map, #39 잠재 배수망·저수위 하천, #40 P06 맨틀 오류 복구·자산 검증·선 표시,
  #42 Younger/Older 전환 중 지구 유지 수정을 배포했다.
- #38·#39 검토와 과학적 격자 간격의 한계는 [073](20260916_jikhanjung_073_river_review_fixes.md),
  P06 구현·검증·보류 항목은 [074](20260916_jikhanjung_074_mantle_review_fixes.md)에 기록되어 있고 인덱스에 등록됐다.
- #40은 사용자 배포 요청 후 검증된 head `141ec20`을 main `474f153`으로 병합했다.
- 하천 기능 추가를 포함하므로 v0.13.0으로 올리고 앱·Docker·배포 매니페스트를 맞췄다.
- 073에서 지적한 미재생성 자료를 그대로 배포하지 않도록 수정된 빌더로 109시점과 해당 저수위 필드를 전부 다시 만든다.
  원본 자료 다운로드·과학적 해상도 변경은 없다. 일반·저수위 필드 혼합은 표시 보간이다.

## 배포 전 확인

- 개발 호스트 m710q, 운영 SSH dolfinid → dolfinid-2 / honestjung 확인.
- 운영 사전 스모크: v0.12.0 healthy, PaleoAtlas 90개, 누락 0. 디스크 여유 3.3 GB.
- 최신 main·열린 PR·이슈 확인. 기능 병합 후 다른 열린 PR 없음; #30·#6은 후속 연구/기능 범위다.
- P06 변경은 Django 73개, JS 5개 파일, 처리 수치 검사, Chromium 전체 및 Firefox 검사 통과(074).
- 마이그레이션·seed 변경 없음. 검증된 이미지·자료 쌍과 DB 스냅샷 확인 후 기존 deploy.sh로 교체한다.
  `.env.django`와 운영 DB를 보존하며 v0.12.0을 롤백용으로 유지한다.

## 빌드·배포 결과

- 릴리스 설정 PR [#41](https://github.com/jikhanjung/EarthThruTime3D/pull/41)은 `e481af6`으로 병합했다.
  추가 요청의 구현·화면 검사는 [076](20260916_jikhanjung_076_mantle_age_transition.md)에 기록했다.
  [#42](https://github.com/jikhanjung/EarthThruTime3D/pull/42) 병합 커밋은 `b5e16d0`이다.
- 최종 빌드 소스 `7fe24ba`: 깨끗한 작업 트리에서 빌드했으며 #42 병합에 포함된 커밋이다.
  앱·Docker·매니페스트 버전 모두 0.13.0이다. 초기 준비 이미지는 배포하지 않고 추가 수정 후 다시 빌드했다.
- 일반 하천 109장 + 저수위 31장 = 140장을 모두 수정 빌더로 재생성했다.
  PNG 크기 2048×1024·단일 채널과 완료 목록을 확인했다. 43,057,932 bytes이며
  140장 전부의 SHA-256이 최종 패킹 매니페스트와 일치했다.
- 전체 자료 묶음: 1,066개 파일, 427,503,685 bytes. 운영에서 파일 해시 전부 검증 통과.
- `make check`, Django 73개, JS 5개 파일, 하천 수치 검사 6개 통과.
  최종 이미지 빌드의 Django 검사와 컨테이너 스모크도 통과했다.
- 추가 수정 후 `mantle-transition-browser.mjs`, `mantle-overlay-browser.mjs`,
  전체 `globe-browser.mjs` 통과. 양방향 지구 유지, 오류·취소·팝업 동기화,
  PaleoAtlas·PaleoDEM·모바일·기후·해빙기·마지막 빙기 범위를 확인했다.
- 이미지 `honestjung/earththrutime3d:v0.13.0`:
  `sha256:9920d24b94284386e9920c7a6478603b9377f21d373822c2bf1cff06f792d0f8`.
  개발 호스트의 아카이브를 전송하고 운영에서는 load·기존 deploy.sh 교체만 수행했다.
- 배포 직전 DB 스냅샷 `db-20260915T165029Z.sqlite3`(131,072 bytes), 무결성 검사 통과.
  기존 DB 유지, `.env.django` 배포 전후 SHA-256 일치. 코드 롤백용 v0.12.0을 보존했다.
- 컨테이너 healthy, 호스트 스모크·공개 HTTPS `/healthz` 통과:
  `status=ok`, `version=0.13.0`, DB·스키마 정상, PaleoAtlas 90개, 필수 필드 누락 0.
  배포 후 호스트 디스크 여유 17 GB(별도 정리 작업은 수행하지 않았다).
- 공개 Firefox 검사: 지구본·반투명 Younger/Older(80→60→80 Ma)·연결 팝업·독립 단면·맨틀 통과.
  공개 Chromium 하천 검사: PNG·셰이더·토글·해상도 안내·한영·모바일·저수위·빙기 시간 범위 통과.

## 운영 초기화 장애 확인

배포 준비 중 사용자가 v0.12.0의 “Preparing the globe…” 정지를 보고했다.
운영 Firefox에서 `three` bare specifier를 해석할 import map이 없다는 오류와
canvas 없음 상태를 재현했다. Chromium에서는 표시됐다. 서버 health 정상만으로
브라우저 초기화 정상이라고 판단할 수 없는 사례다. #38 수정이 포함된 v0.13.0 배포 후
공개 Firefox의 지구본 초기화와 맨틀·단면 동작을 다시 확인했다. 같은 기본 주소에서도
`Present Land mask shown`, `aria-busy=false`, canvas 존재로 복구를 확인했다.

## 릴리스 아카이브 SHA-256

| 파일 | SHA-256 |
|---|---|
| image-v0.13.0.tar.gz | `e32c92b697d757c3b1de60fa3712e21077b74559513ed2ae94263108e160756b` |
| data-v0.13.0.tar.gz | `88de6149be22f2e202f714765a6ba23264bffc179e9c2014d303367f5904c846` |
| host-v0.13.0.tar.gz | `ef9ae1e17d5aeb39b4ad48f5a3382fff0c354d8d0c18138a527a71b1944d5e5a` |

운영: https://earththrutime.nopeoplestime.info/
롤백: `bash /srv/earththrutime3d/deploy.sh v0.12.0` (DB 복원 없음).
파생 PNG 기대 해시 manifest·선택 유지보수 등 P06의 남은 범위는 074를 따른다.
