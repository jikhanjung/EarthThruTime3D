# v0.23.0 — 화면 색·배치와 새 표시 레이어 릴리스

상태: 배포 준비 중.

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

## 절차

운영 DB와 `.env.django`를 유지하고 기존 deploy.sh의 자료 검증 → DB 백업 → 교체 →
스모크를 그대로 쓴다. 개발 호스트 m710q에서 빌드해 Docker Hub와 scp로 전달한다.
