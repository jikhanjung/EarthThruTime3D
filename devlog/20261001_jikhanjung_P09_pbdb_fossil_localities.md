# jikhanjung P09 — PBDB 화석 산지를 지구본에 (#81), WegenersDream 방식의 개선판

날짜: 2026-10-01 · 기준 버전: v0.23.0 · 이슈: [#81](https://github.com/jikhanjung/EarthThruTime3D/issues/81) ·
참고: [028](20260913_028_fossil_check.md)(화석으로 지도 검사), #80(위치 핀, v0.21.0), WegenersDream
`docs/PBDB_자료_처리.md`·`docs/PBDB_받기_검토.md`(2026-10-01) · 상태: 계획

## 목적

지금 보이는 나이의 화석 산지(PBDB collection)를 지구본에 점으로 그린다. 각 산지는 **그 나이에 판이 있던 자리**로
옮기고, 누르면 PBDB 기록으로 이어진다. #81(wwolf)이 제안한 층이다. 이 계획은 #81의 설계를 따르면서,
같은 일을 먼저 한 WegenersDream(이하 WD)에서 얻은 규칙과 WD 검토에서 찾은 약점을 고친 방식을 얹는다.

## 1. WD 에서 가져오는 것, 고치는 것, 버리는 것

| WD | 여기서 |
|---|---|
| 점 하나 = 산지 하나. 산출(occurrence)은 미리 싣지 않는다 | **그대로** — 산출은 백만 건이 넘는다 |
| 시점 ±2.5 Myr 창과 연대 범위가 **겹치면** 걸친 모든 시점에 올린다. 중간값 규칙은 빈 시점을 만든다(WD 001) | **그대로**, 창 너비만 이 뷰어의 시점 간격에 맞춘다(§3.3) |
| 연대 범위의 상한이 없다(WD 015) | **그대로**. 028 의 `MAX_AGE_SPAN_MA = 15` 는 지도 검사용이고 화면에는 쓰지 않는다 |
| 모호한 연대 = PBDB 시대 이름의 **등급**(세·기·대…)으로 가른다, 범위 길이로 가르지 않는다. 제4기 안의 이름은 예외(WD 016, tupandactyl 008) | **그대로 옮긴다** — 이를 위해 시대 이름표를 함께 고정한다(§3.2) |
| 좌표는 파이프라인이 **시점마다 미리 돌려** 109 개 파일로 굽는다 | **고친다** — 이 뷰어는 시점이 설정마다 다르고(`steps`·1/5/10 Myr·25 Myr 심부·1 ka 창) 브라우저에 회전 모델이 이미 있다. 판 번호와 도달 나이(reach)만 빌드에서 한 번 구하고, 자리는 핀처럼 브라우저가 `carried()` 로 계산한다(#81 의 스케치) |
| 판이 없으면 PBDB 고좌표(`pgm=scotese`)로 대신한다 | **버린다** — #81: 다른 모델의 좌표를 섞지 않는다. 닿지 않는 산지는 **세고 목록에 남기고** 그리지 않는다 |
| PBDB 고좌표가 없는 산지 46,930 곳을 뺀다(016 까지의 집합을 지키려는 WD 사정) | **버린다** — 현재 좌표만 있으면 우리 모델로 돌린다 |
| 매주 cron 으로 PBDB 를 새로 받는다 | **버린다** — 이 사이트는 이미지·자료 묶음이 해시로 짝지어진 불변 배포다(`docs/operations.md`). 받기는 **판을 올릴 때만**, 새 SHA-256 으로 다시 고정한다 |
| 받은 뒤 파일을 바꾼 다음에 95% 점검을 한다(WD 검토 §3.3·3.4) | **고친다** — 바꿔 끼우기 **전에** 지난 고정본의 행 수와 견준다(§3.1) |
| 이름표에 없는 시대 이름을 센다고 적고 세지 않는다(WD 검토 §3.5) | **고친다** — 세어 `index.json` 에 싣고, 0 이 아니면 빌드가 이름을 적는다 |
| 산지 팝업 500 건, 분류군 찾기 20,000 건에서 말없이 잘린다(WD 검토 §3.1·3.2) | 산출을 PBDB 에 물을 때(§4 2단계 이후)는 **`rowcount` 로 전체 수를 받아 "N 건 중 M 건"** 을 적는다 |
| 분포에 `occs/diversity` 기본 timerule(`major`)을 써 넓은 연대가 빠진다(WD 검토 §3.6) | 분포를 만들 때는 **`timerule=overlap`** 을 적는다 |
| 브라우저가 PBDB 에 바로 묻는다(CORS `*`) | **정할 것**(§5.1) — #81 은 "방문자 브라우저에서 제3자로 요청을 보내지 않는다" 이고, 개인정보 페이지도 "외부 추적 리소스를 쓰지 않는다" 고 적는다 |

## 2. 이 저장소에서 확인한 것 (2026-10-01)

- PBDB 산지 고정본이 이미 있다 — `sources/paleogeography/pbdb-collections.json`: 2026-09-13, 278,284 행, 크기·SHA-256
  고정, 질의는 WD 와 같다(`show=loc,paleoloc,geo,crmod&pgm=scotese`). 지금은 `scripts/check_fossils.py` 만 쓰고
  "not served"
- 028 의 환경 분류는 작업자 결정이다: 확실한 해양·확실한 육상만, 해안·하구·석호·준해안은 어느 쪽에도 넣지 않는다.
  WD 는 연구자 결정으로 해안·석호를 해양, 하구·만을 육상에 넣었다 — **여기서는 028 의 결정을 따른다**(§3.4)
- 회전: `static/core/rotation.js` `RotationModel.rotation(pid, age)`, 판 다각형은 `/plates/<model>/continents.json`.
  핀은 `pins.js` `pinAt`·`reachOf`·`carried`·`drawnAt`, 모델은 `PIN_MODEL = 'paleomap2016'`(globe.js). 파이썬 짝은
  `scripts/assess_pin.py`, 둘이 맞는지는 `tests/pins.test.mjs` 가 본다
- 시점은 서버가 만든 목록이다(`core/globe.py` `timeline()`): 지도 쌍마다 `steps` 또는 1/5/10 Myr, 지도 없는 25 Myr
  심부 시점, PaleoDEM 전용 1 ka 창(`deglacial`·`lastcycle`)
- 층 틀: 해안선 층이 본보기다 — `*_DERIVED_DIR` 설정 → `index.json` → 문맥 → `json_script` → `FileResponse` 뷰 →
  globe.js 에서 받아 그리기. gzip·ETag·SHA-256 은 `core/experiment_assets.py` `asset_response`. 묶음은
  `deploy/pack_data.py` 가 자료마다 명시해 싣고 `deploy/verify_bundle.py` 가 시작 때 모두 대조한다
- 누르기는 `pickLonLat()`(레이캐스터)뿐, 떠 있는 팝업·툴팁 틀은 없다. 화면 문구는 서버 `viewer_strings()` → gettext
- CSP 는 없다 — 브라우저 `fetch` 를 막는 것은 없다
- PBDB API 의 `datainfo` 는 지금 **CC0** 라고 답한다(2026-10-01 확인, #81 도 같다). 매니페스트는 CC BY 4.0(2013 공지)이다

## 3. 설계

### 3.1 받기 — 다시 고정하는 절차 (`scripts/fetch_pbdb.py`)

지금은 받는 스크립트가 없다(028 때 손으로 받았다). WD `fetch.py` 에 검토의 고침을 넣어 만든다:

1. 산지 표와 **시대 이름표**(`intervals/list.json?all_records&vocab=pbdb`)를 **둘 다 임시 파일에** 받는다
2. 산지는 CSV **행**을 센다(줄바꿈이 든 칸이 있다). 헤더에 쓰는 칸(`collection_no`·`lng`·`lat`·`max_ma`·`min_ma`·
   `early_interval`·`late_interval`·`environment`·`n_occs`)이 모두 있는지, 이름표 레코드에 `type`·`b_age` 가 있는지 본다
3. **지난 고정본의 `records` 보다 5% 넘게 적으면 멈춘다**(임시 파일을 지우고, 고정본은 그대로). PBDB 가 실제로 대량
   정리를 했으면 `--allow-shrink` 로만 넘긴다
4. 모두 통과한 뒤에 두 파일을 제자리로 옮기고, 매니페스트의 `retrieved_at`·`bytes`·`sha256`·`records` 를 **둘 다** 고친다 —
   이름표와 산지가 같은 날의 짝이다(WD 는 이름표를 먼저 바꿔 끼운다)
5. 매니페스트 변경은 커밋에 남고, 판을 올리는 PR 에서 검토된다. 자동 cron 은 두지 않는다

`check_fossils.py` 는 같은 고정본을 계속 쓴다 — 고정본을 올리면 028 의 수도 달라지므로, 그 PR 에서 다시 돌려 적는다.

### 3.2 가공 — `scripts/build_fossils.py`

입력: 고정본 두 개(크기·SHA-256 대조 후), PALEOMAP 판 다각형·회전(`data/derived/plates/paleomap2016/`).

- 산지마다: 연대 없음·현재 좌표 없음은 세고 뺀다. `old < young` 이면 바꾼다
- **판 번호·도달 나이**: 현재 좌표를 품은 다각형을 `assess_pin.py` 와 같은 규칙으로(겹치면 가장 오래 가는 것) 한 번 찾는다.
  다각형 없음·판이 산지의 **가장 젊은 나이**까지도 못 닿음은 따로 세고 `collection_no` 목록을 남긴다(#81 표의
  "No polygon"·"Older than the polygon's reach")
- **모호한 연대**: WD `intervals.py` 규칙을 옮긴다 — 등급 `epoch·subepoch·period·era·eon·bin` 이면 모호, 제4기 바닥
  (여기 층서표의 2.58 Ma) 이하의 이름은 예외. **이름표에 없는 이름은 세고**, 빌드 출력과 `index.json` 에 이름째 적는다
- **환경 갈래**: `m`(확실한 해양)·`t`(확실한 육상)·`x`(가장자리 — 해안·하구·석호·준해안)·`o`(미상). `MARINE`·`TERRESTRIAL`
  집합을 `check_fossils.py` 에서 공용 모듈(`scripts/pbdb_env.py`)로 옮겨 둘이 같은 결정을 쓴다
- 출력(`data/derived/fossils/`):
  - `localities.bin` — 산지마다 고정 길이: 현재 경·위도(양자화), 판 번호, 도달 나이, `max_ma`·`min_ma`, 환경 갈래·모호함 비트,
    `collection_no`. 목표 **gzip 4 MB 이하**(#81 추정 3–4 MB)
  - `details/<nnn>.json` — 누를 때만 받는 조각(번호 범위별): 이름·지층·시대 이름 둘·원 환경 용어·국가·`n_occs`
  - `index.json` — 고정본의 날짜·SHA-256, 수(받은 행·뺀 까닭별·닿지 않음·모호·모르는 이름), 모호한 이름 목록(분류군
    찾기를 할 때 같은 규칙에 쓴다), 파일마다 bytes·sha256

### 3.3 그리기 — 어느 시점에 무엇을

- **표면**: PALEOMAP 틀인 `paleoatlas2016`(기본)·`paleodem2018` 에서만 켤 수 있다. `scotese2002` 는 경도가 PALEOMAP 과
  어긋나므로 해안선 층처럼 내지 않는다. 판 모델 겹쳐 보기(Merdith 등)를 골라도 화석은 **표면의 모델**(PALEOMAP)로 돈다 —
  #81: 표면을 그린 모델로 돌리고 다른 곳의 고좌표를 쓰지 않는다
- **자리**: 핀과 같은 길 — `carried(model, locality, age)`, 두 지도 사이는 `drawnAt` 으로 표면 조각이 그려진 자리에 맞춘다.
  한 `THREE.Points` 층, 자리 계산은 시점이 바뀔 때만(판 번호별로 회전을 한 번 구해 같은 판의 산지에 쓴다)
- **어느 산지를 보이나**: 연대 범위 `[min_ma, max_ma]` 가 **시점 ± 창**과 겹치면. 창은 **그 시점과 이웃 시점 사이 간격의
  절반**으로 한다 — 5 Myr 간격이면 WD 와 같은 ±2.5 Myr, 1 ka 창이면 ±0.5 ka. 간격이 달라도 시점 사이의 산지가 빠지지 않고,
  넓은 연대의 산지는 걸친 모든 시점에 나온다. 심부 25 Myr 시점은 ±12.5 Myr 라 한 시점에 많이 오르는데, 그 자리가 한 순간의
  지도가 아니라는 것을 화면이 적는다
- **모양·색**: 정해진 연대 = 원, 모호한 연대 = 세모(WD 016). 색은 환경 갈래 넷. 모호한 연대 보이기 스위치(기본 켬)
- **누르면**: `pickLonLat()` 에 가장 가까운 산지(화면 몇 px 안)를 찾아 정보 패널에 적는다 — 이름·연대(시대 이름과 Ma)·
  모호함·지층·환경·오늘날 국가·**그 자리는 모델의 계산**이라는 말·PBDB 기록 링크. 떠 있는 팝업 틀은 만들지 않는다
- **화면이 말해야 하는 것**(#81 그대로): 연대는 한 순간이 아니라 구간이다 · 채집 자리는 관찰이고 옛 자리는 회전 모델의 계산이다 ·
  점은 생물이 살던 곳이 아니라 사람이 채집한 곳이다(북미·유럽에 몰린다) · PALEOMAP 해안선은 화석 증거로도 그렸으므로
  해양 화석이 바다에 드는 것은 독립 검사가 아니다(028)
- 문구는 `viewer_strings()` 에 한·영으로 넣는다. 주소(#96)에 층 켜짐을 싣는다

### 3.4 제공과 배포

- `FOSSILS_DERIVED_DIR` 설정 → `core/globe.py` 에 `fossils(source)`(해안선 `coastlines()` 와 같은 꼴, PALEOMAP 표면이 아니면
  None) → `json_script` → `asset_response` 로 gzip·ETag
- `deploy/pack_data.py` 에 자료를 명시하고 `verify_bundle.py` 가 대조한다. `/healthz` 의 필수 항목에는 넣지 않는다
  (기후·얼음처럼 선택 층)
- `LICENSE-DATA.md`·`sources/README.md` 에 PBDB 를 적는다. 라이선스는 §5.3 을 정한 뒤

## 4. 단계 (PR 하나씩)

1. **자료** — `fetch_pbdb.py`(§3.1), 이름표 고정, `pbdb_env.py`, `build_fossils.py`, 파이썬 시험(창 겹침·모호함·제4기 예외·
   모르는 이름 세기·줄어듦 거절·도달 나이). 화면 변화 없음. #81 의 다섯 절 표를 전체 고정본으로 다시 재어 PR 에 적는다
2. **층** — 체크박스·점·누르기·정보 패널·문구·주소, `pack_data.py`. 화면이 바뀌므로 CHANGELOG(무엇·PR·devlog·
   보는 법: 표면 `paleoatlas2016`, 예: 66 Ma·252 Ma, "화석 산지" 켜기)
3. **산지의 산출 목록** — §5.1 을 정한 방식으로. 묻는다면 `occs/list?coll_id=…&show=class&rowcount`, 받은 수가 전체보다 적으면
   "N 건 중 M 건 · PBDB 에서 전체" 를 적는다
4. (나중) **분류군 찾기** — WD 의 찾기(`base_name`·`timerule=overlap`)와 산출 시대 분포(`occs/diversity` 에 `timerule=overlap`,
   `rowcount` 로 잘림 표시). 찾은 산지는 PBDB 고좌표가 아니라 `collection_no` 로 우리 `localities.bin` 에서 찾아 같은 판 회전으로
   놓는다. 우리 파일에 없는 산지는 그리지 않고 센다

## 5. 정할 것

1. **산출을 어떻게 보이나** (3단계부터)
   - (가) PBDB 기록 링크만 — 제3자 요청 없음, #81·개인정보 페이지와 맞다. **1·2단계는 이것으로 한다**
   - (나) WD 처럼 브라우저가 누를 때 PBDB 에 묻는다 — 코드가 가장 적다. 개인정보 페이지에 "산지를 누르면 브라우저가
     paleobiodb.org 에 묻는다" 를 적어야 한다
   - (다) Django 가 PBDB 에 대신 묻고 캐시한다 — 방문자 브라우저는 우리 서버만 본다. 서버가 바깥으로 나가는 길과 캐시가 는다
   - 권고: 2단계까지 (가)로 내고, 쓰임을 본 뒤 (나)와 (다) 가운데 연구자가 고른다. 분류군 찾기(4단계)는 (나) 또는 (다) 가 있어야 한다
2. **#81 의 물음에 대한 답** — 이 계획의 가정: 표면은 PALEOMAP 둘(기본 atlas 포함), 첫 판은 산지만(분류군 무리 거르기 없음,
   환경 갈래 거르기만), 묶음 +4 MB 는 받아들인다. #81 에 답을 달고 wwolf 와 누가 어느 단계를 맡을지 나눈다 — #81 은 wwolf P02 로
   쓰겠다고 했으나 wwolf P02 는 해류(#89)로 갔다
3. **라이선스** — API 는 CC0, 매니페스트는 CC BY 4.0. API 의 답(받은 날 기록)을 매니페스트에 적고, 어느 쪽이든 PBDB 와 원 문헌을
   밝힌다
4. **환경 갈래** — 028(가장자리는 어느 쪽에도 넣지 않음)을 따른다고 적었다. WD 처럼 해안·석호를 해양에 넣으려면 연구자가 정한다
5. **고정본을 언제 올리나** — 2026-09-13 본으로 시작한다. 올리는 것은 판 PR 의 일로, 주기는 정하지 않는다

## 6. 확인하는 법

- 파이썬 규칙과 `pins.js` 가 같은 자리를 내는지: 절마다 표본 산지를 `assess_pin.py` 와 브라우저 계산으로 견준다(`tests/pins.test.mjs` 확장)
- PBDB `pgm=scotese` 고좌표와의 거리(중앙값·p90)를 절마다 적는다 — 028 의 255 Ma 중앙값 1.13° 와 #81 의 수십 km 가 기준
- 시점마다 오른 산지 수, 닿지 않은 산지 수, 모호한 비율을 `index.json` 에 두고 화면 설명에 쓴다
- WD 와 같은 날의 고정본이면 같은 시점(예: 255 Ma, ±2.5 Myr)의 산지 집합이 WD 의 것과 견줘, 차이가 "PBDB 고좌표 없음"(WD 가 뺀 것)과 "판이 닿지 않음"(여기서 뺀 것) 으로 모두 설명되어야 한다
