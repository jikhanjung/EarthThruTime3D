# jikhanjung 060 — v0.10.3: 빙하 구멍 메우기, 마지막 빙하기 물러남의 조각

날짜: 2026-09-15

## 한 것

- wwolf 의 두 PR 을 차례로 main 에 합쳤다.
  - #28(wwolf 005): 빙하 마스크 속 50만 km² 미만의 빈틈을 메우고, 가장자리를 위도 방향으로도 흐린다.
  - #29(wwolf 006): 현재 시점의 저수위를 아틀라스의 최후빙기 지도 대신 NADI-1(CC BY 4.0)과
    DATED-1(CC BY 3.0)의 6~24 ka 조각 18장으로 바꿨다. `/globe/ice-low/<id>/<ka>.png`.
  - #29 는 #28 위에 쌓여 있었다. `devlog/README.md` 색인만 부딪혀 두 쪽을 모두 남겼다.
- 자료: `fetch_paleodem.py --manifest sources/ice.json` 로 두 압축 파일을 받아 해시를 확인하고,
  `build_ice.py` 로 빙하 마스크 전체와 저수위 조각을 다시 만들었다.
- v0.10.3 배포.

## 확인

- `make check`, `make test` 51개, `tests/ice_check.py` 6개, `npm test` 13개 통과.
