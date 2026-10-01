# jikhanjung P10 — 현재의 지구: 위성 영상 바탕에 바람·해류·구름 (GSM "움직이는 지구" 옮기기)

날짜: 2026-10-02 · 기준 버전: v0.23.0 · 참고: GSM(koprifossillab 003·007·008·010–016·018, P02·P03,
v0.34.0–v0.38.3, 2026-10-01 17:50–21:50 KST), GSM `docs/바람_시각화.md`·`docs/구름_시각화.md`·
`docs/ECCO2_해류_시각화.md`, GSM wetherilli 086(온 지구 배경), [wwolf P02 — 해류·해수면 온도(#89, 열린 PR)](https://github.com/jikhanjung/EarthThruTime3D/pull/89) ·
상태: 계획

## 목적

0 Ma 의 지구를 **위성 영상(Blue Marble) 바탕**으로 보이고, 그 위에 GSM 이 2026-10-01 에 들인 세 가지 —
**바람(입자)·해류(입자)·구름(덮개)** — 를 얹는다. 지금까지 0 Ma 는 다른 시대와 같은 고도 격자의 색칠이었다.

ETT 의 과거는 지질 시간이다. 날 단위·달 단위의 지난 날씨를 재생할 까닭이 없다. 그래서 0 Ma 에는
**"지금" 한 장**만 보인다 — 바람·구름은 판(release)을 만들 때의 최신 관측·분석 한 시각, 해류는 평년값 한 장.
날짜 고르개도 재생도 없다. 이렇게 하면 묶음은 10 MB 안팎만 늘고, 방문자 한 사람이 받는 양은 1–4 MB 다.

## 1. GSM 에서 가져오는 것, 고치는 것, 버리는 것

| 항목 | GSM | 여기서 |
|---|---|---|
| 바탕 영상 | GIBS WMS `BlueMarble_ShadedRelief_Bathymetry`(기본 `bm`), 브라우저가 타일을 직접 받음 | **고친다** — 같은 영상을 빌드 때 한 장으로 받아 묶음에 넣는다(방문자 브라우저의 제3자 요청 금지) |
| 바람 | GFS 0.25°(지금, 매시 받기) + ERA5(지난, 날마다) | GFS 받기·풀기(`gfs.py`)를 **그대로**, 단 **판을 만들 때 분석(f000) 한 장**만. ERA5 는 **버린다** |
| 모델 구름 | GFS·ERA5 `tcc/lcc/mcc/hcc`, 회색 L PNG, 두 시각을 CPU 로 섞어 `toBlob` | GFS `tcc` 한 장만 **그대로**. 섞기가 없으니 알파 변환만 셰이더에서 |
| 위성 구름 | NOAA GMGSI 매시 적외선 합성, 0.1° RGBA 를 서버가 칠함 | 받기·칠하기(`gmgsi.py`)를 **그대로**, 바람과 **같은 시각 한 장**만 |
| 해류 | ECCO2 cube92 표층, 달마다 한 장, 1992–2019, 재생 | **고친다** — 같은 받기(`ecco.py`)로 달마다 한 장씩 받아 **평균한 평년값 한 장**. 107.5° 경도 밀림(`SHIFT u=(430,-1) v=(429,-1)`), 남쪽 두 줄 쓰레기값(`JUNK_ROWS=2`, 밀기 전에 0), NAS 마지막 바이트 누락(1 바이트 더 묻기), `MAX_SPEED=3.0` 은 다 옮긴다 |
| PNG 형식 | 바람 RGB(R=u,G=v, 칸마다 min/max 는 `index.json`), 해류 RGB(+B=바다 마스크), 구름 L, 위성 RGBA | **그대로** |
| 입자 | Canvas 2D 덮개, 경위도에서 옮기고 Cesium/OL 이 화면에 투영 | 옮기기·색·수명·꼬리는 **그대로**, 투영·숨기기·뿌리기는 Three.js 와 우리 평면 투영 셋으로 **다시 쓴다** |
| 색·범례 | 바람 따뜻한 8 색·가는 선, 해류 청록 8 색·굵고 느린 선, `flowLegend` | **그대로**(상수 `WIND_REF/PX/LIFE/FADE`, `OCEAN_*` 포함, 해류 `OCEAN_REF` 는 평균값에 맞춰 다시 잰다 — §6) |
| 시간 축 | 날짜·달 고르개, ▶ 재생, 두 장을 `w` 로 섞기, GFS 예보 두 장을 지금 시각으로 섞기 | **버린다** |
| 매시 받기 | `hourly.sh`·cron·`hourly_status.json`·`/healthz/` 신선도, `usage.py` | **버린다** — 받기는 판 PR 에서 손으로 한 번(§3.2). 실시간은 다음 계획(§5 (다)) |

## 2. 이 저장소에서 확인한 것 (2026-10-02)

- **방문자 브라우저는 제3자에게 묻지 않는다**(개인정보 쪽, P09 §5.1). GSM 처럼 GIBS 타일을 브라우저에서 받을 수 없다.
- **자료 묶음은 판마다 고정되고 해시로 짝지어진다**(`deploy/pack_data.py`·`verify_bundle.py`, `/runtime` 읽기 전용).
  자료를 새로 받는 cron 은 없다. 판 때 받은 한 시각은 이 약속 안에 들어간다.
- **0 Ma 만의 레이어는 이미 있다** — 지각(`crust.js`, `age === 0` 이 아니면 `data-crust="unavailable"`),
  Natural Earth 얼음·지금 강. 같은 문을 쓴다. 0 Ma 는 그냥 `frame.age === 0` 이다.
- 지구본은 Three.js 0.186, 반지름 1, 표면은 한 `ShaderMaterial`(`globeMaterial()`, `static/core/globe.js`) 의
  `mode` 0–5(map·mask·relief·temp·veg·rain). 셰이더는 표본기 16 개 중 13 개를 쓴다 — **바탕 영상 하나는 더 넣을 수
  있지만 구름은 따로 그려야 한다.** 평면 셋(equirect·mollweide·equalearth)은 셰이더의 `locate()` 가 경위도로 되돌린다.
- 그리기 고리 `renderer.setAnimationLoop` 이 `delta` 를 이미 셈하고, `reducedMotion` 이 있다.
- 받기·굽기는 `scripts/*.py` + `requirements-processing.txt`(이미지에는 들지 않는다), 원자료 `data/sources/<주제>/`,
  결과 `data/derived/<레이어>/`, 고정 목록 `sources/*.json`, 내주기는 `core/experiment_assets.py` `asset_response()`(sha256·immutable).
- **GIBS WMS 는 한 번의 GetMap 으로 온 지구를 준다** — `BBOX=-90,-180,90,180`, 8192×4096 JPEG 3.1 MB,
  4096×2048 0.94 MB(오늘 받아 봄). 남극·그린란드가 흰 얼음, 바다는 깊이 음영이다.
- 해류는 wwolf P02(#89, 열린 계획 PR)가 **NOAA 표류 부이 연평균 고정 그림**으로 먼저 잡아 두었다. 둘 다 평년값이라
  겹친다 — §5 (가).

## 3. 설계

### 3.1 위성 영상 바탕 — `scripts/fetch_bluemarble.py`

- GIBS WMS 1.3.0 GetMap, `LAYERS=BlueMarble_ShadedRelief_Bathymetry`, EPSG:4326, 8192×4096 과 4096×2048 두 장.
  `sources/bluemarble.json` 에 URL·받은 날·바이트·sha256·인용(NASA Earth Observatory / EOSDIS GIBS, 공공 영역)을 적는다.
  줄어든 응답(오류 이미지)은 크기 하한으로 막는다. 한 번 고정하면 판마다 다시 받지 않는다.
- 결과 `data/derived/bluemarble/{8192,4096}.jpg` + `catalogue.json`. 처음에는 4096 을 쓰고, 가까이 다가가고
  `MAX_TEXTURE_SIZE ≥ 8192` 일 때만 8192 를 받는다.
- 그리기: `globeMaterial()` 에 `mode 6`(`sat`) 과 표본기 하나(`satMap`)를 더한다. 0 Ma 에서만 고를 수 있고,
  **0 Ma 의 기본 표면이 된다.** 0 Ma 를 떠나면 사람이 고른 표면(없으면 지금 기본)으로 돌아간다. 위성 영상에는 이미
  얼음이 그려져 있으므로 `sat` 일 때 얼음 덧칠은 끄고, 강은 그대로 고를 수 있다. 3D 기복(`relief3d`)은 지금처럼
  고도 격자로 들어 올린다 — 영상과 격자의 해안이 몇 칸 어긋날 수 있다(확인 항목).
- 화면 설명: "NASA Blue Marble(2004 년 무렵 위성 합성)". 0 Ma 라도 오늘 찍은 사진은 아니다.

### 3.2 지금의 바람·구름 — `scripts/fetch_present_weather.py`

판 PR 에서 손으로 한 번 돌린다. 한 시각 `T` 를 정해 바람·모델 구름·위성 구름을 다 그 시각으로 맞춘다.

- `T` = 받는 때에 NOMADS 에 올라온 가장 새 GFS 주기(00·06·12·18 UTC, 주기 뒤 약 4 시간). `--cycle YYYYMMDDHH` 로 고를 수 있다.
- **GFS 분석(f000)**: NOMADS grib filter 로 `UGRD/VGRD` 의 `10 m`·`250 mb` 와 `TCDC entire atmosphere` 만.
  GSM `gfs.py` 의 풀기(격자 1440×721 검사, `stepType == "instant"`, `typeOfLevel` 로 250 mb `TCDC` 거르기, % ÷ 100)를 옮긴다.
  → `10m.png`·`250hPa.png`(RGB, 경도 −180 시작) + `cloud.png`(L). 약 1.7 MB.
- **GMGSI**: `noaa-gmgsi-pds` 의 `GMGSI_LW/YYYY/MM/DD/HH/` 에서 `T` 시각 파일 하나. GSM `gmgsi.py` 의 메르카토르 → 경위도
  옮기기와 알파식(`SAT_CLEAR, SAT_FULL = 105, 210`, `0.92·clip(...)^0.9`)을 그대로 쓰되 0.2°(1800×900)로 내려 약 0.9 MB.
  ±72.7° 너머는 비어 있다.
- 결과 `data/derived/present/<T>/…` + `index.json`(`t`, `run`, u/v 범위, 출처별 인용). 판마다 새 `<T>` 로 바꾸고 옛 것은 지운다.
  `sources/present_weather.json` 에 받은 URL·바이트·sha256 을 적는다.
- `requirements-processing.txt` 에 `eccodes`(GRIB2, 휠에 라이브러리 포함)·`h5py`(GMGSI HDF5)를 더한다. 앱 이미지에는 들지 않는다.
- 인용: "NOAA/NCEP GFS 0.25° (public domain)", "NOAA/NESDIS GMGSI — geostationary IR mosaic (public domain)".

### 3.3 해류 평년값 — `scripts/build_ecco2_mean.py`

- GSM `ecco.py` 로 1992-01–2018-12 의 달마다 15 일에 가장 가까운 3 일 평균(324 장, UVEL·VVEL 각 4 MB Range 읽기,
  모두 약 2.7 GB, 약 2 시간)을 받는다. 원자료는 `data/sources/ecco2/` 에 두고 이어 받는다.
- 경도 밀림·쓰레기 줄·`MAX_SPEED` 를 고친 뒤 칸마다 u·v 를 따로 평균한다(속력이 아니라 벡터 평균 — 소용돌이는 지워지고
  평균 흐름이 남는다). 육지(u=v=0)는 평균에서 뺀다.
- 결과 `data/derived/ocean/ecco2-mean.png`(R=u, G=v, B=바다) + `index.json`(`depth_m: 5`, 기간, 장 수). 약 0.6 MB.
  한 번 고정하면 판마다 다시 굽지 않는다.
- 인용: "ECCO2 cube92 (NASA JPL·MIT) · Menemenlis et al. 2008". 모델의 평균이지 관측이 아니라는 것, 발트해는 모델에
  없다는 것을 설명에 적는다.

### 3.4 그리기 — `static/core/flux.js`(새 모듈, import map 에 더함)

- **입자**: 지구본 캔버스 위에 `pointer-events:none` 2D 캔버스 둘(해류 아래, 바람 위). 옮기기는 GSM 그대로
  (`k` = 화면 한 칸의 미터 × PX / REF, `lat += v·k/M_PER_LAT`, `lon += u·k/(M_PER_LAT·max(0.05,cos lat))`).
  장(field)이 한 장이라 섞기가 없다 — GSM 의 `windAt`/`oceanAt` 에서 `w` 를 뺀 것이다.
  - 투영: 지구본은 `onSphere(lon,lat,1)` → `tiltedView()` 카메라로 `project`, 뒷면은 `dot(점, 카메라 방향) ≤ 0` 이면 숨김.
    평면은 `projection.js` 의 `place*` 와 `meridian`. 화면 한 칸의 미터는 카메라 거리(지구본)·평면 축척에서 셈한다.
  - 뿌리기: 무작위 화면 칸을 지구본은 광선-구 교차, 평면은 `unplace*` 로 경위도로 되돌린다(해류는 바다에 떨어질 때까지 30 번).
  - 카메라가 바뀌면 캔버스를 비운다. `reducedMotion` 이면 입자를 멈춘 한 장으로 그린다.
  - 3D 기복을 켜면 높은 산이 입자를 가릴 수 없다(입자는 반지름 1 에 그린다) — 알려진 한계로 적는다.
- **구름**: 반지름 1.004 의 투명한 껍질(평면에서는 같은 판 위 한 장)에 따로 `ShaderMaterial`. 위성은 RGBA 를 그대로,
  모델은 회색 `f` 를 `alpha = 0.9·f^0.85` 로 셰이더에서 바꾼다. 평면은 `globeMaterial` 의 `locate()` GLSL 을 함께 쓴다.
  표면 셰이더의 표본기는 건드리지 않는다. 구름을 켜면 입자를 가리지 않도록 불투명도 0.75(GSM 과 같다).
- **자료 시점 표시** — 레이어마다 시점이 다르므로 켠 레이어의 시점이 늘 화면에 보여야 한다. 카드를 접어도 보이게
  다음 세 자리에 둔다.
  - **연대 표시 옆**(`0 Ma` 아래 한 줄): 켠 것만 짧게 — "바람·구름 2026-10-0X 00 UTC(09 시 KST) · 해류 1992–2018 평균 ·
    바탕 Blue Marble 2004". 꺼진 레이어는 적지 않는다.
  - **범례 머리**: 바람 범례에 "GFS 분석 2026-10-0X 00 UTC", 해류 범례에 "ECCO2 1992–2018 평균",
    구름에 "GMGSI 2026-10-0X 00 UTC" 또는 "GFS 분석 …".
  - **카드·출처**: 위 시점에 더해 "판 v0.2X.0 을 만들 때 받은 것 — 실시간이 아니다" 와 인용.
  - 시각은 `index.json` 의 `t` 에서만 만든다(화면에 시각을 손으로 적지 않는다). UTC 를 먼저, 방문자 시간대를 괄호로.
  - "지금" 이라는 말을 실시간처럼 쓰지 않는다. 버튼 이름도 "바람" 이지 "지금 바람" 이 아니다.
  - 브라우저 시험은 표시 문자열이 `index.json` 의 `t` 와 같은지, 레이어를 끄면 그 시점이 줄에서 빠지는지 본다.
- **켜기**: ☰ 메뉴에 `#wind`·`#currents`·`#clouds`(`aria-pressed`), 바람 높이(10 m / 250 hPa 제트), 구름 종류(위성 / 모델).
  0 Ma 일 때만 보이고, 떠나면 셋 다 꺼지고 `data-flux="unavailable"`. 보기 주소 `wind=10m|250hPa`, `currents=1`,
  `clouds=sat|model`. 범례는 GSM `flowLegend` 를 옮겨 왼쪽 위 범례 자리에. 문자열은 `viewer_strings()` + 영어 msgstr.

### 3.5 제공과 배포

- `config/settings/base.py` 에 `BLUEMARBLE_DERIVED_DIR`·`PRESENT_DERIVED_DIR`·`OCEAN_DERIVED_DIR`, `/runtime/...` 기본.
- `core/flux.py`: `catalogue()`·`globe_config()`·`flux_asset()` — `core/crust.py` 를 본뜬다. 주소는 `globe/bluemarble/<크기>.jpg`,
  `globe/present/<T>/<이름>.png`, `globe/ocean/ecco2-mean.png`. 목록은 `json_script 'globe-flux'` 로 쪽에 싣는다(따로 묻지 않음).
- `deploy/pack_data.py` 에 더하고 `verify_bundle.py` 가 해시를 본다. `/healthz` 는 이 레이어를 요구하지 않는다(없으면 버튼이 숨는다).
- 묶음에 더해지는 양: 바탕 4 MB + 바람·구름 약 2.6 MB + 해류 0.6 MB ≈ **7 MB**(지금 약 483 MB).
  방문자가 받는 양: 바탕 0.9 MB(가까이 가면 3.1 MB 더) + 켠 레이어 몇백 KB 씩.
- **판 절차**: 판 PR 에서 `fetch_present_weather.py` 를 돌려 새 `<T>` 를 고정한다. `deploy/README.md` 의 판 순서에 한 줄 더한다.

## 4. 단계 (PR 하나씩)

1. **위성 바탕 자료** — `fetch_bluemarble.py`, `sources/bluemarble.json`, 내주기·묶음. 화면 변화 없음.
2. **0 Ma 위성 바탕** — `mode 6`, 0 Ma 기본 표면, 보기 주소 `surface=sat`, 문서·CHANGELOG. *여기까지만으로도 쓸모 있다.*
3. **해류 평년값 + 입자** — `build_ecco2_mean.py`, `flux.js` 의 입자 틀(투영·뿌리기·꼬리)·해류 카드·범례. 입자 틀을
   해류로 먼저 세우는 까닭: 한 번 굽고 나면 다시 받을 일이 없고, 바다 마스크로 뿌리기까지 다 시험된다.
4. **지금의 바람** — `fetch_present_weather.py`(GFS 바람), 10 m/250 hPa, 때 알리기.
5. **구름** — 같은 스크립트에 GFS `tcc`·GMGSI, 구름 껍질 셰이더.
6. 판(release) — 처음으로 `<T>` 를 고정하고, 첫 화면 무게를 재고, `docs/globe-viewer.md` 에 "Present-day Earth" 절,
   `deploy/README.md` 판 순서.

각 화면 PR 은 CHANGELOG 에 "확인:" 줄(0 Ma, ☰ 메뉴의 어느 버튼)을 단다.

## 5. 정할 것

**정함(2026-10-02, 저장소 주인)**: 모두 추천대로 — (가) ECCO2 평균으로 시작하고 #89 에서 wwolf 와 맞춘다,
(나) 구름 기본은 위성, (다) 실시간은 다음 계획, (라) 해류 평년값은 한 장.

**(가) wwolf P02(#89)와 해류 평년값을 어떻게 나누나.** 둘 다 "지금 바다의 평균 흐름" 한 장이다.
(1) ECCO2 평균(모델, 0.25°, 빈 곳 없음). (2) P02 의 NOAA 표류 부이 연평균(관측, CC BY 4.0, 0.25°, 부이가 드문
바다는 성기다). PNG 형식(R=u,G=v,B=바다)이 같으면 어느 쪽이든 그리는 쪽은 바뀌지 않는다.
**추천 (1)로 시작하되 #89 에서 wwolf 와 맞춘다** — 관측이 낫다고 보면 3 단계의 자료만 (2)로 바꾼다. 해수면 온도와
옛 바다는 P02 가 맡는다.

**(나) 구름의 기본.** (1) 위성(GMGSI, 관측, 극지 빈 곳) (2) 모델(GFS `tcc`, 온 지구). **추천 (1)** — 위성 영상 바탕
위에 위성 구름이 어울리고, 관측이다. 극지가 비는 것은 설명에 적고 모델로 바꿀 수 있게 둔다.

**(다) 실시간(GSM 처럼 매시)은 다음 계획.** 쓸 수 있는 `live/` 볼륨, 호스트 타이머, 굽기 venv, healthz 신선도,
`docs/operations.md` 의 자료 안전 약속 고치기가 따른다. 이 계획의 받기·굽기 코드는 그때 그대로 쓴다.

**(라) 해류 평년값을 달마다 12 장으로 할까.** 인도양 계절풍 해류처럼 철마다 뒤집히는 흐름은 한 장 평균에서 사라진다.
12 장이면 약 7 MB. **추천: 한 장으로 시작**, 필요하면 같은 받은 자료로 다시 굽는다(다시 받을 필요 없음).

## 6. 확인하는 법

- 0 Ma(`?masks=paleodem2018&age=0`, 기본 자료도) 에서 지구본·평면 셋에 위성 바탕. 남극·그린란드 얼음, 해안이 고도 격자·
  해안선 레이어와 어긋나는 정도. 휴대폰(4096 장)과 데스크톱(8192 장).
- 해류: 걸프 해류·쿠로시오·남극 순환류·적도 해류가 제자리에서 바른 방향으로(107.5° 밀림 고침 확인), 북극에 튀는 값 없음.
  평균은 순간값보다 느리므로 `OCEAN_REF`(GSM 0.5 m/s)를 평균 속력 분포를 보고 다시 정한다.
- 바람: 250 hPa 에서 편서풍 제트, 10 m 에서 무역풍.
- 자료 시점: 연대 옆 줄·범례 머리·카드의 시각이 모두 `index.json` 의 `t` 와 같고, 켠 레이어의 것만 보임.
- 구름: 열대 수렴대 띠, 위성 구름과 GFS 구름이 같은 시각에서 대체로 겹침, ±72.7° 너머 위성은 빔.
- 0 Ma 를 떠나면 셋 다 꺼지고 `data-flux="unavailable"`, 돌아오면 다시 켜짐.
- 브라우저 네트워크 탭에 제3자 요청이 없음. `make check`·`make test`·`npm test`, 새 `tests/flux-browser.mjs`(`data-*` 속성).
