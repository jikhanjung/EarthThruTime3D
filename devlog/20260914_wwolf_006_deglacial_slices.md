# wwolf 006 — 현재의 저수위를 마지막 빙하기 물러남의 복원으로

날짜: 2026-09-14 · 브랜치: feature/ice-deglacial-slices (wwolf 005 위에 쌓음) · 이슈 #7의 뒷정리

## 문제

현재 시점의 저수위는 아틀라스의 LGM 지도였다. 그 지도는 시베리아 중부(60–180°E 구간에 1,170만 km²,
북아메리카 구간은 1,880만 km²)와 알래스카·베링기아를 희게 칠하고 코르디예라는 회색 산지로 그려
구멍투성이였다. 0에서 −130 m 사이는 두 거리장의 선형 섞임이라, 로렌타이드가 허드슨 만 쪽으로
물러나고 코르디예라가 갈라지는 실제 순서와는 달랐다.

## 라이선스 확인

ICE-6G_C와 ICE-7G_NA(토론토 대학 페이지): 라이선스 없음, 인용 요청만. GLAC-1D: 같음. Batchelor et al.
2019(OSF 7jen3): 라이선스 미설정. Dalton et al. 2020 QSR 부록: Elsevier all rights reserved(공개
사본은 CC BY-NC-ND). 그래서 쓴 것은 둘이다.

- NADI-1, Dalton et al. 2023 QSR 321, 108345. Zenodo 10.5281/zenodo.8161764, CC BY 4.0. 로렌타이드·
  코르디예라·이누이시안 가장자리, 25–1 ka 0.5 kyr, optimal/min/max, WGS84 경위도.
- DATED-1, Hughes et al. 2016 Boreas 45, 1. PANGAEA 10.1594/PANGAEA.848117, CC BY 3.0. 브리튼·
  스칸디나비아·스발바르–바렌츠–카라 가장자리, 25–10 ka 1 kyr, most-credible/min/max, 북극 람베르트
  정적 방위 투영.

PaleoMIST 1.0(Gowan et al. 2021, PANGAEA, CC BY 4.0)은 전 지구 1° 두께장이지만 2.5 kyr 간격에
3.5 GB라 이번에는 쓰지 않았다. 남극·그린란드를 나중에 채울 후보다.

## 한 일

- `sources/ice.json`에 두 아카이브를 고정했다(크기, SHA-256). `fetch_paleodem.py --manifest`로 받는다.
- `build_ice.py`: 1천 년마다 오늘의 빙하 ∪ NADI-1 OPTIMAL ∪ DATED-1 mc를 2048×1024에 래스터화해
  거리장 `paleodem-0000-ice-low-<ka>.png`로 쓴다. DATED-1의 투영은 Snyder(1987)의 식으로 직접
  역투영했다(큰 다각형의 면적이 파일의 Shape_Area와 0.5% 안에서 맞는다). 각 조각의 해수면은
  Spratt & Lisiecki 스택의 그 나이 값을 현재에서 거슬러 올라가는 최소값으로 단조화한 것이고, 더
  낮추지 않는 조각(1–5, 20, 25 ka)은 버린다. 18장이 남고(6–19, 21–24 ka), −130 m가 24 ka다.
- 서버: `/globe/ice-low/<id>/<ka>.png`, 프레임에 `ice_lows` 목록(나이, 해수면, 부피, 면적표, URL).
  옛 사이드카의 dict형 저수위는 없는 것으로 친다.
- 페이지: offset을 감싸는 두 조각을 고르고(0 m는 프레임 자신의 장) 셰이더가 두 텍스처를
  `iceLowT`로 섞는다. 가장 깊은 조각 아래는 면적 법칙. `data-ice-low`는 보이는 조각의 나이(ka).
- 패커는 `*-ice-low-*.png`를 모두 싣는다. 해수면 노트 문구와 영어 번역, `docs/globe-viewer.md`.

## 한계

남극·그린란드·아이슬란드와 산악 빙하는 현재 범위 그대로다(두 복원의 범위 밖). 조각 사이는 여전히
선형 섞임이지만 간격이 1천 년이라 가깝다. 다른 빙하기 시점은 면적 법칙뿐이고, 조각 목록이라는 틀은
복원이 있는 시점이면 어디든 같은 방식으로 채울 수 있다.

## 검사

`tests/ice_check.py`(역투영 왕복), Django 51, 브라우저 검사(현재 −130 m에서 `data-ice-low` 24.0, 0 m에서
빈 값), 패커.
