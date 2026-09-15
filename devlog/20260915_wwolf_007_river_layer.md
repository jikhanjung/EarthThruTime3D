# wwolf 007 — 하천 층: 격자 위로 물을 흘린 잠재 배수망

날짜: 2026-09-15 · 브랜치: feature/river-layer (main 위) · 이슈 #30

## 배경

고도 격자 시리즈에 강을 보여 줄 수 있는가. 답은 "과거의 강을 그린 공개 자료는 없고, 격자 위로
물을 흘려 얻는 잠재 배수망은 있다"였다. 이 기록은 그 확인 과정과 구현, 그리고 무엇이 관측이고
무엇이 계산인지의 구분이다.

## 라이선스 확인

- Salles, Husson, Lorcery & Boggiani, Paleo-Physiography Project(HydroShare 컬렉션
  0106c156507c4861b4cfd404022f9580). 지형 진화 모델 goSPL을 우리와 같은 Scotese & Wright
  2018 격자에 Valdes et al. 2021의 강수를 주어 돌린 결과로, 109개 시기(0, 3, 11, 15, 20, 26 …
  541 Ma, 우리 5 Myr 시점과 다름)의 0.05° NetCDF에 하천 유량(`wflux`), 유역 번호, 내륙 호수
  깊이, 강수, 퇴적물 유량이 들어 있다. 시기당 0.9 GB, 전체 약 77 GB. 컬렉션 표지는 CC BY지만
  부분별로는 287–449 Ma만 CC BY 4.0이고 0–127, 131–280, 456–541 Ma와 고도 전용·유역별 유량
  자료는 모두 CC BY-NC-SA 4.0이다. 이 저장소의 파생 자료는 CC BY 4.0(jikhanjung 056)이므로
  NC-SA 부분은 비교용으로만 쓸 수 있다.
- Natural Earth 10 m `rivers_lake_centerlines`: 공공 영역, 현재만.
- Bristol BRIDGE의 Valdes et al. 2021 자료 페이지에는 라이선스가 없다(이슈 #6에 적음).

그래서 직접 계산했다. 입력은 이미 고정된 6분 PaleoDEM 격자(CC BY 4.0)뿐이고, 필요한
도구(scipy, scikit-image)는 `requirements-processing.txt`에 이미 있다.

## 방법 (`scripts/build_rivers.py`)

1. 6분 격자를 2048×1024 텍스처로 다시 표본화하고 z > 0을 육지로 본다.
2. 웅덩이를 넘치는 높이까지 메운다(scikit-image의 grayscale reconstruction). 경도 방향으로
   격자를 세 번 이어 붙인 뒤 가운데를 취해, 날짜변경선을 가로지르는 분지도 하나로 메운다.
3. 육지의 각 칸은 여덟 이웃 중 실제 거리로 가장 가파른 쪽으로 물을 보낸다. 메워진 호수는
   평평하므로 배출구부터 안쪽으로 파도처럼 방향을 정하고, 그 파도 번호로 합산 순서를 정한다.
4. 높은 칸부터 내려가며 상류 면적(km²)을 더한다.
5. 텍스처는 그림이 아니라 셰이더가 자르는 장이다. 각 텍셀은 반경 4텍셀 안 하천 칸들의
   "크기 − 0.35 × 거리"의 최댓값이고, 크기는 상류 면적의 log10을 10³–10⁷ km²에서 0..1로 놓은
   값이다. 페이지는 0.25(1만 km²)에서 자르므로 선의 굵기가 크기를 따라가고, 두 격자의 장을
   섞으면 해안선 거리장처럼 그럴듯한 중간이 된다. 한쪽에 장이 없으면 그쪽 가중치가 0이라
   그 구간에서 망이 사라진다.

비는 고르게, 증발은 없이 두었으므로 결과는 유량이 아니라 유역 면적이다. 해수면은 격자의 0 m다.

## 확인

- 현재(0 Ma): 아마존 유역 5.65 Mkm²(발표치 6.3–7.0), 하구 0.6°S 51.6°W. 콩고·나일·니제르·
  미시시피·매켄지·오비·예니세이·레나·아무르·양쯔·갠지스·머리가 제자리에 나온다.
- 내륙 분지 실험: 메운 깊이가 50/100/200 m를 넘는 분지를 막힌 것으로 두면 육지 143 Mkm² 중
  73/97/118 Mkm²만 바다에 닿는다. 격자가 매끈해 한 칸보다 좁은 협곡이 막혀 있기 때문이다:
  콩고 분지(깊이 255 m), 쓰촨 분지(583 m), 판노니아 평원(303 m)이 실제로 막힌 차드(120 m),
  타림(367 m), 에어(90 m)와 구별되지 않는다. 그래서 모든 분지가 넘치게 두었다. Salles et al.도
  같은 가정("depression-less surface")을 썼다.
- 날짜변경선: 64열만 덧대어 메우면 530 Ma에서 2047열의 16칸이 어디로도 흐르지 못한다.
  세 번 이어 붙이면 없어진다. `directions`는 이런 칸이 남으면 멈추도록 해 두었다.
- 격자당 10–74초(캄브리아기의 큰 대륙이 가장 오래 걸림), 109장 43분. 텍스처 하나 약 300 KB, 109장 33 MB.
- `manage.py test`(52), `tests/rivers_check.py`(섬의 모든 물이 바다에 닿는가, 웅덩이가 넘치는가,
  날짜변경선 위의 섬이 하나로 흐르는가, 장이 원뿔인가), 브라우저 스위트의 하천 토글 검사.

## 남은 것 (이슈 #30)

- 저수위와 최후빙기. 현재 격자를 빙하 슬라이스의 해수면마다 다시 흘리면 강이 드러난 대륙붕
  (순다, 도거랜드의 해협강, 베링기아)을 건넌다. 얼음 아래는 빙하 마스크의 거리장으로 포물선
  얼음 표면(h = k√d)을 격자에 더해 흘리면 융빙수가 가장자리를 따라 흐르고 빙하호가 차서
  넘친다(아가시 → 미시시피). 얼음 두께 자체는 PaleoMIST 1.0(CC BY 4.0, 3.5 GB)이 후보다.
- 호수 깊이(메운 높이 − 격자)를 둘째 채널로.
- 현재 시점에 Natural Earth 강을 겹쳐 비교.
- 시점 사이는 두 장의 선형 섞임이라 강의 역사가 아니라 페이드다. 지형 진화 모델 없이는
  더 할 수 없고, 그것은 표시가 아니라 연구다.

## 바뀐 파일

- `scripts/build_rivers.py`, `tests/rivers_check.py` (새로)
- `core/globe.py`, `config/urls.py`: `rivers_path`, 프레임의 `rivers`, `/globe/rivers/<id>.png`,
  `rivers_available`
- `templates/core/home.html`, `templates/core/about.html`, `locale/en/LC_MESSAGES/django.po`:
  `#rivers` 토글, `#river-note`, 출처 줄
- `static/core/globe.js`: `loadRivers`, `applyRivers`, `riverA/riverB/riverWeight`, 셰이더의 하천
- `deploy/pack_data.py`: `*-rivers.png` 포장(없으면 건너뜀)
- `core/tests.py`, `tests/globe-browser.mjs`, `docs/globe-viewer.md` "Rivers"
