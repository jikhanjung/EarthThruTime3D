# 022 — Scotese 회전 모델로 경도 비교

날짜: 2026-09-13

## 발단

021에서는 Scotese 쪽을 지도에서 분할한 육지로만 비교했다. 받아 둔 PALEOMAP PaleoAtlas 묶음
(`docs/pdf/Scotese_PaleoAtlas_v3.zip`)에 Scotese 자신의 GPlates 회전 모델과 판 다각형이
들어 있어, 같은 비교를 회전끼리 할 수 있게 됐다.

## 한 것

- `scripts/pack_paleomap.py`: zip에서 회전 파일과 판 다각형을 직접 읽어
  `data/derived/plates/paleomap2016/`에 다른 모델과 같은 형식으로 묶는다. GPML 읽기와 회전
  병합은 `pack_plates.py`의 함수를 그대로 쓴다. `sources/plate-models/`에 목록 파일을 만들지
  않으므로 뷰어와 배포 묶음에는 들어가지 않는다.
- `scripts/measure_longitude_offsets.py`: `paleomap` 구역을 더했다. 지도 맞춤, PALEOMAP과 Merdith,
  T&C와 PALEOMAP의 지점 비교, T&C 두 층을 PALEOMAP에 대 본 위도를 출력한다. 목록 파일이 없는
  모델은 묶음에 적힌 범위를 쓴다.

## 걸린 것

처음 돌렸을 때 0 Ma 지도 맞춤만 최적 회전 +80°, 겹침 0.26으로 튀었다. 다각형 196개의 유효
기간이 0 Ma에서 0 Ma였고, 이것들이 현재 시각에만 켜져 지구의 99%를 덮었다. 0.018 Ma에서는
육지 비율이 0.38로 정상이었다. 기간이 0인 다각형을 묶을 때 빼자 0 Ma가 +1°, 0.66으로 돌아왔다.
다른 시대와 지점 비교는 100 Ma 이상이라 영향이 없었다.

## 결과

- PALEOMAP 회전 모델을 2002년판 지도에 맞추면 356 Ma까지 ±11°, 390~514 Ma에서 −23~−56°다.
  지도와 모델의 판이 달라 개정 효과와 구분할 수 없다.
- PALEOMAP과 Merdith는 306 Ma까지 경도 12° 안, 그 이전 20~70°다.
- T&C와 PALEOMAP은 306 Ma에 약 20°, 425 Ma에 90~180° 벌어진다. 고생대 경도에서 T&C가
  다른 두 모델과 갈라진다는 021의 결론이 Scotese 자신의 회전 모델로도 확인됐다.
- 회전 파일에는 고생대 경도 규칙이 적혀 있지 않다. 판 001 "Hot Spot to PMAG"는 항등 회전이고,
  신생대 아프리카 극만 열점 흔적 문헌(O'Connor and Duncan 1990)을 인용한다.

`docs/palaeolongitude.md`에 5.4절로 표를 싣고 요약과 6절 표를 고쳤다.
