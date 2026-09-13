# 035 — PaleoDEM 고도 격자를 세 번째 마스크 소스로

날짜: 2026-09-13 · 브랜치: feature/paleodem-elevation (PR #1)

## 문제

17장 웹 JPEG는 저해상도이고 글자와 현대 해안선이 박혀 있으며 높이가 없다. 같은 날 main에
2016 PaleoAtlas 마스크와 판 모델이 올라와, 고도 격자는 그 구조 안의 세 번째 소스로 넣는다.

## 자료

Scotese & Wright (2018) PALEOMAP PaleoDEMs, Zenodo 5460860, CC BY 4.0. 1° 격자 109장과
6분 격자, 540 Ma~현재 5백만 년 간격, 미터 단위. `sources/paleodem.json`에 SHA-256으로 고정.

## 구현

- `MASK_SOURCES`에 `paleodem2018`. 항목에 `file`이 있으면 이 소스다. 텍스처는
  `PALEODEM_DERIVED_DIR`(기본 `data/derived/paleodem/`).
- `series_items()`: 540 Ma 이전은 2016 아틀라스 지도 3장(600·690·750 Ma)을 마스크로 앞에
  붙여 112개 시점. 같은 판본이라 2002년 지도를 쓰지 않는다.
- 전부-아니면-무: 필드가 하나라도 없으면 `mask_source`가 기본 소스로 물러난다. 이 시리즈는
  필드가 없는 시점에 보여 줄 지도가 없기 때문이다. `/healthz`는 보여 주는 소스를 센다.
- `scripts/build_paleodem.py`: 격자를 2048×1024로 겹선형 보간, 0 m에서 잘라 거리장(R),
  높이 12비트(G 상위, B 하위 4비트). 거리 변환은 `segment_paleoatlas.py`의 것을 쓴다.
- 뷰어: 셰이더 `mode` 0 지도 / 1 마스크 / 2 고도. 고도 모드는 거리장으로 해안을 자르고
  높이를 hypsometric 램프로 칠한다. 필드는 `<img>` 대신 2D 캔버스에서 바이트를 읽어
  `DataTexture`로 올린다(삼성 휴대폰이 색 관리로 두 채널을 낮게 읽었다). 텍스처 캐시 12개.
- 시대 이름은 main의 `period_label`(ICS 경계)을 그대로 쓴다. 문구는 `{% trans %}`와
  `locale/en`으로.

## 확인

`make check`, Django 테스트(신규 5개). 브라우저 확인은 아틀라스 필드가 갖춰진 뒤 기록한다.

## 남은 것

음영 기복·식생 없는 색(PR #3), 기온(#4), 해수면(#5), 현재 빙하(#8)가 이 위에 쌓인다.
운영 번들은 텍스처를 싸지만 기본 소스는 아틀라스다.
