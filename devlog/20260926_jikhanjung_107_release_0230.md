# v0.23.0 — 화면 색·배치와 새 표시 레이어 릴리스

상태: 2026-09-26 운영 배포·공개 Chromium 검증 완료.

## 변경

하루에 올라온 WWolf의 PR 일곱 건을 검토·수정해 병합한 결과를 배포한다.

- [#90](https://github.com/jikhanjung/EarthThruTime3D/pull/90) 모형 강수 색을 ColorBrewer
  BrBG로(사막이 갈색). [#93](https://github.com/jikhanjung/EarthThruTime3D/pull/93) 기온 색을
  RdYlBu로 바꾸고 색 화면 아래에 산맥 음영을 넣었다. 두 PR의 색맹 ΔE 수치와 평지 음영 계수
  (0.749153), 범례 정지점을 재현해 확인했다(wwolf 016·017).
- [#92](https://github.com/jikhanjung/EarthThruTime3D/pull/92) 하천 → **잠재 하천**, 강수 범례
  아래 주의. [#94](https://github.com/jikhanjung/EarthThruTime3D/pull/94) 색 범례를 지도 위로
  띄우고 정보 패널의 지구 내부·안내문을 접었다.
- [#96](https://github.com/jikhanjung/EarthThruTime3D/pull/96) 주소에 투영·표면·음영·해수면·
  스위치를 싣는다. [#97](https://github.com/jikhanjung/EarthThruTime3D/pull/97) 시간축에 기후·
  생물 사건 16개를 표시한다(wwolf 019). [#98](https://github.com/jikhanjung/EarthThruTime3D/pull/98)로
  토아르시움절·세노마눔절 표기를 맞췄다.
- [#95](https://github.com/jikhanjung/EarthThruTime3D/pull/95) 평면 지도에 산맥을 표시한다
  (wwolf 018). **새 자료** `mountain-ranges.json` 약 700 KB가 묶음에 들어간다. 원본
  `sources/mountain-ranges.json`(Natural Earth 10 m regions, 공공 영역)을 SHA-256으로 검증하고
  `scripts/build_mountain_ranges.py`로 생성했다. 현재 29개 산맥 546 마크, 규칙이 그중 91 %에
  300 km 안으로 닿으며, 과거 격자는 250 Ma 130개에서 50 Ma 963개다.

## 검토에서 고친 것

- #96: 시간 범위의 해수면이 주소에 적혀 창을 나가도 남아 전체 시리즈가 −120 m로 그려지던 것,
  `0`·`1` 밖의 플래그를 켬으로 읽던 것, 메뉴를 여는 것만으로 `age`가 박히던 것.
- #97: 8 px 마크에서 글자가 잘려 색만 단서로 남던 것, 마크 13개가 슬라이더 앞 탭 정지를
  13개 만들던 것, 첫·마지막 시점의 매칭 창이 절반이던 것.
- #94: 폰에서 뜬 범례가 지구본 한복판을 가리던 것.
- 별도로 main에: 릴리스 `sed`가 `deploy/README.md`의 빙기 하천 도입 버전을 매번 바꾸던 것,
  브라우저 검사 여섯 개의 `expect` 타임아웃이 5초로 남아 부하에서 흔들리던 것.

## 빌드·운영 배포

- PR #90, #92–#99를 병합한 깨끗한 main `827a056`에서 개발 호스트 m710q가 `build.sh v0.23.0`으로
  빌드했다. Django 85개, 패킹, 이미지 스모크 통과.
- 자료 **1,289개, 482,999,048 bytes**. v0.22.0 대비 새 파일 1개(`mountain-ranges.json`,
  718,066 bytes), 변경·삭제 0개. 호스트 묶음은 v0.18.1 이후 해시가 같다.
- 이미지 digest: `sha256:28f29b11d8e02ed1f41f2084503c797267f1968d8e13bacfa2e4701470b41d5c`.
  Docker Hub에 push하고 dolfinid-2에서 digest로 pull했다. 아카이브는 scp 후 SHA-256 대조.
- 배포 전 dolfinid-2: v0.22.0 healthy, 디스크 여유 32 GB.
- 기존 `deploy.sh v0.23.0`이 자료 1,289개 검증 → DB 백업 → 컨테이너 교체 → 스모크를 완료했다.
- DB 백업 `db-20260926T034148Z.sqlite3`(파일명 UTC), 무결성 검사 통과. 운영 DB 유지,
  `.env.django` 배포 전후 동일. 컨테이너 healthy.
- 공개 `/healthz`: `ok`, `0.23.0`, DB·스키마 정상, PaleoAtlas 필수 90개·누락 0.
- 공개 `/globe/ranges.json`을 내려받아 빌드 묶음과 SHA-256이 같음을 확인했다.
  공개 HTML에 `globe.js?v=0.23.0`, `#event-marks`, `globe-ranges`, "입체 지형", "잠재 하천".
- 공개 Chromium: `?view=equalearth&surface=temp`가 주소대로 열리고, 떠 있는 색 범례가 보이며,
  산맥 546 마크(`data-ranges` present), 사건 마크 13개에 탭 정지 1개, 시간 창에서 강수 화면과
  주소에 `sea` 없음을 확인했다. `tests/climate-browser.mjs`, `tests/pin-browser.mjs`,
  `tests/view-address-browser.mjs`, 13만 년 창 집중 검사 통과. 콘솔·네트워크 오류 없음.
  스크린숏 `data/screenshots/public-0230-{temp-ranges,rain}.png`.
  `tests/globe-browser.mjs` 전체는 종전과 같이 공개 배포의 원본 지도 비공개 설정에서 멈춘다.
  Firefox BiDi는 실행하지 않았다.
- 운영: https://earththrutime.nopeoplestime.info/
- 롤백: `bash /srv/earththrutime3d/deploy.sh v0.22.0` (DB 복원 없음). v0.21.0도 남아 있다.

### 릴리스 묶음 SHA-256

```text
e6410cb6c935bb1966ad1c85852a253415f4675967ad6bb922ac28999397f961  earththrutime3d-image-v0.23.0.tar.gz
da08a72dbb4c2caca0d428dcbb60e67711a44f7688f593e87c35234be8a8b25b  earththrutime3d-data-v0.23.0.tar.gz
c459ab2d2c8759e87c33aa61e1c81f53ce62b941706dcdb9c0c94118828e5563  earththrutime3d-host-v0.23.0.tar.gz
```
