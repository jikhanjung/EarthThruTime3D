# jikhanjung 101 — 13만 년 창의 26–80 ka 빙상을 PaleoMIST로

날짜: 2026-09-18 · 기준 버전: v0.18.1 · 브랜치: feature/paleomist-window · 이슈: [#59](https://github.com/jikhanjung/EarthThruTime3D/issues/59) · 검토: [jikhanjung 100](20260918_jikhanjung_100_glacial_window_paleomist_review.md)

## 범위

100의 권고대로 (b) 단계만 구현했다. 해수면은 스택을 유지하고, 26–80 ka 빙상을 유사 자료
대신 PaleoMIST 1.0의 접지 빙상으로 바꾸며, 그 구간의 하천을 같은 빙상 위로 다시 라우팅했다.
지각 침강 표시(c)는 하지 않았다. 81–130 ka는 유사 자료 그대로다.

## 자료 생성

- `scripts/paleomist.py`: PaleoMIST 격자를 읽는 공용 모듈. `build_rivers.py`가 쓰던 읽기
  코드를 옮겼고 `paleomist_step`의 결과는 같다(하천 필드 2.5–25 ka 10장 재생성 결과와
  이전 배포본 비교는 아래).
- `scripts/build_ice.py`: NADI/DATED 조각 1–25 ka 뒤에 `paleodem-0000-ice-low-26…80.png`
  55장을 쓴다. 각 나이는 감싸는 2.5 ka 두 스텝의 부호 거리장을 선형으로 섞은 것이다.
  PaleoMIST 빙상은 현재 빙하 위에 얹되, NADI/DATED 조각이 현재 빙하 밖에 더한 얼음의
  3° 이내(`MODEL_REACH_DEGREES`)에만 남긴다. 남극·파타고니아·산악은 조각과 같이 현재 범위다.
  `ice-sources.json`의 `lows`에 `source: paleomist`, `lowers: false`, 그 나이의 스택
  해수면으로 들어가고, `model_levels`에 PaleoMIST 자체 해양 평균 해수면 33개를 넣는다.
- 1–25 ka 조각 25장과 `sheets`·`grids`는 재생성 전과 sidecar 값이 동일하다. 조각 80장
  22.7 MB(새 55장 약 15 MB). 현재 빙하 밖·조각 범위 밖이라 버린 PaleoMIST 얼음은 스텝당
  지표의 0.3–1.1%다(대부분 남극 접지선 확장·파타고니아).
- `scripts/build_rivers.py --ice --ice-to 80`: 32 스텝 전부, 스텝당 약 50초. 해수면은
  종전대로 25 ka까지 held 값, 그 뒤 스택 값. 2.5–25 ka 10장은 배포 중인 v0.17.0 파일과
  바이트 단위로 같고 sidecar 앞 10개도 같다(공용 모듈로 옮긴 읽기 코드의 회귀 검사).
  27.5–80 ka 22장은 `lowers: false`. 32장 13.8 MB, 모두 패커의 RGB 헤더 검사 통과.
  묶음은 v0.17.0 대비 약 25 MB 는다.

## 서버·페이지

- `window_frames`: `source: paleomist` 조각은 `ice_kind` `reconstructed`, 제목
  "PaleoMIST 1.0, N ka", 출처 PANGAEA DOI. 나머지 경로는 dated와 같다(`deglacial.url`).
- `rivers_ice_steps`(새로 분리): 창 프레임은 `lowers`와 무관하게 모든 스텝을 받는다.
  전체 시리즈의 현재 프레임은 종전대로 `rivers_ice_of`가 `lowers` 스텝만 준다.
- `riverChoice`: 창 프레임(`deglacial.age_ka`)은 나이로 두 스텝을 골라 섞는다. 마지막
  스텝(80 ka)보다 오래되면 종전의 해수면 기준으로 돌아간다. 셰이더·uniform 변경 없음.
- `showIceKind`: `data-ice-kind` `reconstructed`, 캡션 "모델 복원 빙상", 안내
  `#ice-model-note`(한영). 유사 자료 안내의 "25 ka보다 오래된"은 나이 고정 문구를 뺐다.
- 창의 해수면 색띠에 PaleoMIST 곡선을 점선(`.sea-model`)으로 겹쳐 그린다.

## 검사

- `make check`, Django 83개, `npm test`, `tests/ice_check.py` 9개(가짜 격자로 footprint
  규칙·스텝 섞기·해양 평균 곡선 검사 2개 추가), `tests/rivers_check.py` 12개 통과.
- 26 ka는 25 ka 조각과 이어지고, 40 ka에 허드슨만이 열리며, 60 ka 빙상이 40 ka보다
  크고, 80 ka는 현재에 가깝다(마스크 그림으로 확인).
- Chromium 브라우저 검사(`tests/globe-browser.mjs`, `tests/river-browser.mjs`) 전체 통과.
  `lastcycle` 40 ka: `data-ice-kind` reconstructed, 모델 안내 보임, `data-river-ice` 40.0,
  색띠에 `.sea-model` 점선; 100 ka: analogue, 안내 보임, `data-ice-low` 채워짐.
  스크린숏 `data/screenshots/globe-cycle-40ka.png`.
- Firefox BiDi 검사와 운영 배포는 하지 않았다. 배포 시 자료 재생성은
  `build_ice.py` 전체(약 6분)와 `build_rivers.py --ice --ice-to 80`(약 30분)이다.

## 남은 것

- #59의 지각 침강 표시(c): 빌더가 스텝별 바다 마스크를 내보내는 설계를 먼저 정한다(100).
- PaleoMIST 최대 MIS 3 시나리오(`a1`)는 아카이브 재다운로드가 필요하다.
