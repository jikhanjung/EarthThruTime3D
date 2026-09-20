# 변경 이력

운영 https://earththrutime.nopeoplestime.info 에 배포된 릴리스별로 무엇이 바뀌었고
화면에서 어떻게 확인하는지 적는다. 배포 절차·해시·검증 결과는 각 항목이 가리키는
릴리스 devlog에, 구현 상세는 [docs/globe-viewer.md](docs/globe-viewer.md)에 있다.

화면 용어: **☰ 메뉴**는 지구본 아래 조작 패널의 설정 버튼, **정보 패널**은 오른쪽 위
"정보" 버튼으로 여닫는 패널, **고도 격자**는 표시 자료 선택(`?masks=paleodem2018`),
**시간 범위**는 고도 격자에서 "지구의 시간" 옆 선택(전체 시대 / 최근 2.5만 년 / 최근 13만 년)이다.
빙기 시점의 화면은 "발표된 복원 · 계산한 결과 · 가정"을 캡션과 안내문으로 구분한다.

## 다음 릴리스

위치 핀: 한 곳을 찍고 시간을 따라가기 ([#80](https://github.com/jikhanjung/EarthThruTime3D/pull/80), [wwolf P01](devlog/20260919_wwolf_P01_location_pin_feasibility.md)·[014](devlog/20260919_wwolf_014_location_pin_measurements.md)·[015](devlog/20260919_wwolf_015_location_pins.md))

- ☰ 메뉴에 **위치 핀**이 생겼다. 켜고 지도를 누르면 핀이 놓이고(하나부터 셋까지), 핀은 그 땅이 실린
  판을 따라 시간축을 움직인다. 핀의 자리는 관측이 아니라 PALEOMAP 회전 모델(Scotese 2016)의 계산이며,
  겹쳐 보기에서 어떤 모델을 골라도 핀은 이 모델로 옮긴다. 바탕 지도와 같은 판본이어서 고도 격자에서
  옮긴 곳의 99.3 %가 제 대륙 위에 머문다(옮기지 않으면 50 %).
- 정보 패널에 핀마다 오늘의 좌표, 판 번호, 지금의 자리(누르면 그 핀이 가운데 오도록 화면을 돌린다),
  지우는 ×가 나오고, 핀이 둘 이상이면 쌍마다 대원 거리를 오늘의 거리와 함께 적는다. 같은 판 위의 두
  핀은 거리가 변하지 않는다(강체 판). 300 Ma 이전의 거리는 모델에 따라 두 배까지 다르며, 쌍별 폭은
  아직 보이지 않는다.
- 모델이 그 땅을 옮길 수 있는 한계(다각형의 시작 시각과 회전 자료의 끝 가운데 이른 쪽)보다 오래된
  시각에는 핀이 사라지고 그 한계를 적는다. 바다에는 핀을 놓을 수 없다.
  Scotese 2002 지도에서는 300 Ma 이전에 핀을 그리지 않는다. 시간 창에서는 핀이 제자리에 선다.
- 주소에 `pin=경도,위도;경도,위도`로 실려 공유된다. 스위치를 끄면 지도·패널·주소에서 모두 사라진다.

확인: 고도 격자 → ☰ 메뉴 **위치 핀** → 200 Ma에서 지도를 누른다. 또는
`?masks=paleodem2018&age=200&pin=126.98,37.57;-87.63,41.88;2.35,48.86`(서울·시카고·파리)을 연다.
패널에 "판 604 · 지금 46.2°N 133.9°E"와 "2–3 3,940 km (오늘 6,650 km)"가 보인다. "지금 …"을 누르면
서울이 화면 가운데로 온다. 450 Ma로 가서 아스타나(`pin=71.43,51.13`)를 보면 "모델에서 420 Ma까지만"이라고
나온다. 450 Ma의 시카고가 옅은 파랑 위에 서 있는 것은 어긋남이 아니라 로렌시아를 덮은 얕은 바다다.

## v0.20.0 — 2026-09-19

시간 창의 모형 식생·강수 ([#75](https://github.com/jikhanjung/EarthThruTime3D/pull/75), wwolf 013, [jikhanjung 103](devlog/20260919_jikhanjung_103_release_0200.md))

- 두 시간 창(최근 2.5만 년·13만 년)의 모든 시점에 Krapp et al. (2021)의 0.5° 모형 기후를
  얹었다. "모형 식생"은 BIOME4 생물군계를 식피 순서 7단계로 묶은 것, "모형 강수"는 연 강수량이다.
  복원이 아니라 HadCM3 통계 에뮬레이터의 결과이며, 아프리카 습윤기의 녹색 사하라를 재현하지 못한다.
- 자료 131장(11 MB). 전체 시대 화면에는 나오지 않는다.

확인: 고도 격자 → 시간 범위 "최근 13만 년" → ☰ 메뉴에 **모형 식생**·**모형 강수** 버튼이
생긴다. 21 ka에서 식생을 켜면 시베리아·티베트·안데스가 툰드라(보라), 아프리카 숲이 파편화된다.
정보 패널에 범례와 "모형 기후 표시 중" 안내(사하라 한계 포함)가 보이고, 캡션에 "모형 식생"이
붙는다. 8 ka에서도 사하라는 사막색이다. 전체 시대로 돌아가면 두 버튼이 사라진다.

## v0.19.0 — 2026-09-18

13만 년 창의 26–80 ka 빙상을 PaleoMIST로 ([#72](https://github.com/jikhanjung/EarthThruTime3D/pull/72), 이슈 #59, [jikhanjung 100](devlog/20260918_jikhanjung_100_glacial_window_paleomist_review.md)·[101](devlog/20260918_jikhanjung_101_paleomist_window_ice.md)·[102](devlog/20260918_jikhanjung_102_release_0190.md))

- 26–80 ka의 빙상이 "해수면이 같았던 후퇴기의 모양"(가정)에서 PaleoMIST 1.0(Gowan et al. 2021)의
  접지 빙상 복원으로 바뀌었다. NADI-1·DATED-1 윤곽이 닿았던 북미·유라시아에만 적용하고 그 밖은
  현재 빙하다. 북미는 MIS 3에 허드슨만이 열리는 최소 시나리오다.
- 창의 빙기 하천 필드가 해수면이 아니라 **나이**로 골라지며, 27.5–80 ka 필드 22장이 추가됐다.
- 해수면은 Spratt & Lisiecki 스택 그대로이고, PaleoMIST 자체 해수면(MIS 3에서 30–55 m 높음)을
  색띠에 점선으로 겹쳐 두 자료의 불일치를 보이게 했다.

확인: 시간 범위 "최근 13만 년"에서 40 ka로 가면 캡션에 **모델 복원 빙상**, 정보 패널에
"모델 복원" 안내가 나오고 허드슨만이 열려 있다. 60 ka는 40 ka보다 빙상이 크다(MIS 4).
100 ka로 가면 다시 "가정 빙하" 캡션·안내로 돌아간다. ☰ 메뉴 **해수면 곡선**을 켜면 창의 색띠에
실선(스택)과 점선(PaleoMIST)이 함께 그려진다. 하천을 켜면 40 ka의 하천이 그 시점의 빙상
가장자리를 따른다.

## v0.18.1 — 2026-09-18

절개 뒷면·지구본 조작 수정 ([#67](https://github.com/jikhanjung/EarthThruTime3D/pull/67), [jikhanjung 097](devlog/20260917_jikhanjung_097_interior_navigation_backfaces.md)·[098](devlog/20260918_jikhanjung_098_release_0181.md))

- 지표 절개의 반대쪽 지각·지표가 그려지고, 투명한 지각이 바깥 지표를 덮어 색이 급변하던 것을 고쳤다.
- 모든 지구본(기본·고도 격자·맨틀)에서 pan·zoom·tilt를 같은 방식으로 지원한다.

확인: 정보 패널 **지구 내부 → 지표 절개**를 켜고 지구본을 돌려 절개 반대편을 보면 안쪽이 비어
있지 않다. 지각 불투명도를 100→99%로 바꿔도 지표 색이 튀지 않는다. 오른쪽 드래그로 이동,
휠 클릭 드래그로 기울기가 어느 자료에서나 된다.

## v0.18.0 — 2026-09-17

지구 내부 공통 절개 ([#64](https://github.com/jikhanjung/EarthThruTime3D/pull/64), [jikhanjung 095](devlog/20260917_jikhanjung_095_shared_interior_cutaway.md)·[096](devlog/20260917_jikhanjung_096_release_0180.md))

- CRUST 2.0 지각과 맨틀 근사 중첩이 정보 패널의 **지구 내부** 한 곳에 모였고, 위도·경도 절개 범위를
  공유한다. 날짜 변경선 횡단과 인도–아시아 프리셋을 지원한다. 절개 기본값 Off, 불투명도 70%.

확인: 정보 패널 → 지구 내부 → **지각 두께**와 **맨틀 근사 중첩**을 함께 켜고 **지표 절개**를 켜면
남·북 위도, 서·동 경도 슬라이더 하나로 둘 다 잘린다. **인도–아시아 위치 프리셋**과
**절개 중심으로 이동**으로 위치를 맞춘다.

## v0.17.0 — 2026-09-17

현재 하천·호수 자료 ([#56](https://github.com/jikhanjung/EarthThruTime3D/pull/56), wwolf 011·012, [jikhanjung 094](devlog/20260917_jikhanjung_094_release_0170.md))

- 현재(0 Ma) 격자의 하천을 Natural Earth 강줄기를 따라 다시 흘려, 격자가 막아 놓은 협곡(도나우의
  철문 등)을 제대로 빠져나가게 했다. 오늘의 호수(HydroLAKES)를 평균 깊이로 칠한다.
- 빙기 하천 필드 10장(2.5–25 ka)도 얼음 밖에서는 현재 하천·호수를 쓰도록 재생성했다.

확인: 고도 격자 현재 시점에서 ☰ 메뉴 **하천**을 켜고 도나우 삼각주·아마존을 확대하면 강이 협곡을
따라 바다로 나간다. 오대호·카스피해가 호수(초록 채널)로 칠해진다. 해수면 슬라이더를 내려도
카스피해는 호수로 남는다.

## v0.16.0 — 2026-09-16

CRUST 2.0 현재 지각 두께 ([#60](https://github.com/jikhanjung/EarthThruTime3D/pull/60), [jikhanjung 091](devlog/20260916_jikhanjung_091_crust2_visualization.md)·[092](devlog/20260916_jikhanjung_092_release_0160.md), [docs/crust.md](docs/crust.md))

- 현재(0 Ma)에서 CRUST 2.0의 지각 두께를 색으로, 클릭한 위치의 두께를 km로, 절개층을 1×/5×로
  보여 준다. 2° 원모델의 표시용 재표본화이며 실제 모호면 깊이가 아니다.

확인: 정보 패널 → 지구 내부 → **지각 두께**. 티베트가 가장 두꺼운 색으로 나오고, 지구본을
클릭하면 "약 NN km" 읽기가 뜬다. 과거 연대로 옮기면 지각 표시가 숨고 "현재 지구 자료" 안내가 나온다.

## v0.15.1 — 2026-09-16

맨틀 JS 모듈 분리 ([#55](https://github.com/jikhanjung/EarthThruTime3D/pull/55)·[#57](https://github.com/jikhanjung/EarthThruTime3D/pull/57), [jikhanjung 088](devlog/20260916_jikhanjung_088_mantle_js_modules.md)·[089](devlog/20260916_jikhanjung_089_release_0151.md))

- 화면 변화 없음. 맨틀 렌더링과 조작 코드를 모듈로 나누고 import map에 버전을 붙여 옛 캐시와 섞이지 않게 했다.

확인: 맨틀 근사 중첩과 `/mantle/` 화면이 v0.15.0과 같이 동작하고 콘솔 오류가 없다.

## v0.15.0 — 2026-09-16

빙기 호수 채널·RGB 자료·Firefox 검사 ([#47](https://github.com/jikhanjung/EarthThruTime3D/pull/47)·[#48](https://github.com/jikhanjung/EarthThruTime3D/pull/48)·[#53](https://github.com/jikhanjung/EarthThruTime3D/pull/53), [jikhanjung 083–086](devlog/20260916_jikhanjung_086_release_0150.md))

- 빙기 하천 필드에 얼음에 막힌 호수(지각 침강으로 생긴 웅덩이, 계산 깊이 약 2.5 m부터)를 초록 채널로
  넣었다. 하천 PNG 형식이 RGB로 바뀌어 캐시 키(`format=river-lake-rgb-v1`)를 분리했다.

확인: 시간 범위 "최근 2.5만 년" 12.5 ka에서 하천을 켜면 로렌타이드 빙상 남쪽에 애거시 호수가
초록으로 보이고 동쪽 샹플랭해 쪽으로 넘친다. 10 ka에서는 남쪽 미시시피로 넘친다.

## v0.14.1 — 2026-09-16

맨틀 중첩 기본값 ([#49](https://github.com/jikhanjung/EarthThruTime3D/pull/49), [jikhanjung 081](devlog/20260916_jikhanjung_081_release_0141.md))

- 맨틀 근사 중첩을 켰을 때 절개 Off, 지표 불투명도 70%가 기본이다. 자료 변화 없음.

확인: 맨틀 근사 중첩을 처음 켜면 지표가 반투명해지고 절개는 꺼져 있다.

## v0.14.0 — 2026-09-16

PaleoMIST 빙하 위로 흘린 빙기 하천 ([#44](https://github.com/jikhanjung/EarthThruTime3D/pull/44), wwolf 008, [jikhanjung 077](devlog/20260916_jikhanjung_077_ice_rivers_review.md)·[079](devlog/20260916_jikhanjung_079_release_0140.md))

- 현재 격자의 하천을 PaleoMIST 1.0의 빙상 두께·지각 침강을 얹은 지형 위로 2.5 ka 간격(2.5–25 ka)
  으로 다시 흘렸다. 녹은물이 빙상 가장자리를 따르고, 20 ka의 채널강(Channel River)이 도버 해협을
  지난다(유역 2.65 Mkm²).

확인: "최근 2.5만 년" 20 ka에서 하천을 켜면 라인·템스·엘베가 합쳐져 도버 해협으로 나간다.
전체 시대 현재 시점에서 해수면 슬라이더를 −100 m 아래로 내려도 같은 필드가 섞여 들어온다
(캡션 아래 `data-river-ice`).

## v0.13.0 — 2026-09-16

잠재 배수망(하천 층)·맨틀 리뷰 수정 ([#38](https://github.com/jikhanjung/EarthThruTime3D/pull/38)·[#39](https://github.com/jikhanjung/EarthThruTime3D/pull/39)·[#40](https://github.com/jikhanjung/EarthThruTime3D/pull/40)·[#42](https://github.com/jikhanjung/EarthThruTime3D/pull/42), wwolf 007, [jikhanjung 073](devlog/20260916_jikhanjung_073_river_review_fixes.md)·[074](devlog/20260916_jikhanjung_074_mantle_review_fixes.md)·[075](devlog/20260916_jikhanjung_075_release_0130.md))

- 새 **하천** 층: 109개 고도 격자 각각의 위로 물을 흘려 계산한 잠재 배수망(상류 면적 1만 km² 이상).
  관측이나 복원이 아니며 유량이 아니라 유역 면적이다. 저수위 필드 31장은 해수면을 내리면 섞인다.
- 맨틀 자산 검증·오류 복구, Younger/Older 전환 중 지구본 유지.

확인: 고도 격자 아무 시점에서 ☰ 메뉴 **하천**. 정보 패널의 "하천 표시 중" 안내가 격자 간격
(약 20 km)과 가정을 설명한다. 해수면 슬라이더를 내리면 드러난 대륙붕 위로 강이 이어진다.

## v0.12.0 — 2026-09-15

메인 지구본 맨틀 통합 ([jikhanjung 070](devlog/20260915_jikhanjung_070_globe_mantle_overlay.md)·[071](devlog/20260915_jikhanjung_071_globe_mantle_time_section.md)·[072](devlog/20260915_jikhanjung_072_release_0120.md), [docs/globe-mantle-overlay.md](docs/globe-mantle-overlay.md))

- 메인 지구본 안에 Müller 2022 OPT1의 Slabs/Piles와 핵 참고 구를 근사 좌표로 겹치고, 지표 절개와
  불투명도, 80·60·40·20·0 Ma 시간 전환을 붙였다. 근사 정합이며 새 대류 계산이 아니다.

확인: 정보 패널 → 지구 내부 → **맨틀 근사 중첩**. "맨틀 원본 시점" 80~0 Ma 중 하나로 맞춰지고
지표 절개를 켜면 안쪽 구조가 보인다.

## v0.11.0 — 2026-09-15

맨틀 모형 화면과 인도–아시아 단면 ([jikhanjung 066](devlog/20260915_jikhanjung_066_mantle_source_preview.md)·[067](devlog/20260915_jikhanjung_067_india_asia_section.md)·[068](devlog/20260915_jikhanjung_068_release_0110.md), [docs/geodynamics.md](docs/geodynamics.md)·[docs/india-asia-section.md](docs/india-asia-section.md))

- `/mantle/`: OPT1의 발표된 3D 표면 51시점. 정보 패널·맨틀 화면의 **인도–아시아 A–A′ 단면**
  버튼: 80 Ma–현재 5시점의 단면·3D 지표 팝업. 지각 단축·대류 화살표는 개념도다.

확인: 푸터 "맨틀 모형 실험" 링크, 정보 패널 맨 위의 "인도–아시아 A–A′ 단면" 버튼.

## v0.10.5 — 2026-09-15

시간 범위 "최근 13만 년" ([jikhanjung P02](devlog/20260915_jikhanjung_P02_last_glacial_cycle.md)·[064](devlog/20260915_jikhanjung_064_last_glacial_cycle.md)·[065](devlog/20260915_jikhanjung_065_release_0105.md))

- 130 ka부터 1천 년 간격 131개 시점. 25 ka 이하는 발표된 복원 조각, 그 이전은(당시) 해수면이
  같았던 후퇴기 모양을 빌린 가정 빙하(v0.19.0에서 26–80 ka가 PaleoMIST로 바뀜). 해안선이 잘 움직이도록
  0 Ma 고도 텍스처를 12비트로 올렸다.

확인: 시간 범위 "최근 13만 년". 121 ka는 해수면 0 m 부근에 현재와 같은 빙하, 21 ka는 로렌타이드·
스칸디나비아 빙상과 넓은 대륙붕. 순다 대륙붕·베링 육교를 확대해 비교한다.

## v0.10.4 — 2026-09-15

시간 범위 "최근 2.5만 년" ([jikhanjung P01](devlog/20260915_jikhanjung_P01_deglacial_time_window.md)·[062](devlog/20260915_jikhanjung_062_deglacial_time_window.md)·[063](devlog/20260915_jikhanjung_063_release_0104.md))

- 고도 격자에 시간 범위 선택이 생겼다. 25 ka부터 1천 년마다 NADI-1(북미)·DATED-1(유라시아)의
  빙상 복원과 그 나이의 해수면을 함께 보여 준다. 해수면 슬라이더는 잠긴다.

확인: "지구의 시간" 옆 선택에서 "최근 2.5만 년". 슬라이더가 25 ka~0 ka가 되고 해수면 슬라이더가
잠긴 채 값만 바뀐다. 캡션에 "NADI-1 · DATED-1, N ka".

## v0.10.3 — 2026-09-15

빙하 구멍 메우기·후퇴기 조각 ([#28](https://github.com/jikhanjung/EarthThruTime3D/pull/28)·[#29](https://github.com/jikhanjung/EarthThruTime3D/pull/29), wwolf 005·006, [jikhanjung 060](devlog/20260915_jikhanjung_060_release_0103.md))

- 빙하 마스크의 50만 km² 미만 빈틈을 메우고 가장자리를 위도 방향으로도 흐렸다. 현재 시점의 해수면
  가정 화면이 아틀라스 그림 대신 NADI-1·DATED-1 조각을 해수면으로 섞는다.

확인: 전체 시대 현재 시점에서 ☰ 메뉴 **빙하**를 켜고 해수면 슬라이더를 −50, −100 m로 내리면
북미·유라시아 빙상이 발표된 윤곽대로 자란다.

## v0.10.0–v0.10.2 — 2026-09-14/15

3D 지형 조작 ([jikhanjung 053–058](devlog/20260914_jikhanjung_057_release_0100.md))

- 선 레이어(판 경계·해안선)가 3D 지형을 따라가고, 기울기·방향 조작이 생겼다. v0.10.1은 휠 클릭
  드래그로, v0.10.2는 두 손가락 제스처와 짧은 화면의 메뉴 배치.

확인: 고도 격자에서 확대하면 지형이 솟고(☰ **3D 지형**, "지형 음영" ×5·×20), 휠 클릭 드래그
또는 Shift+드래그로 기울인다.

## 그 이전

v0.9.x 이하의 변경은 [devlog/README.md](devlog/README.md)의 인덱스와
[jikhanjung 033 releases_and_prune](devlog/20260913_033_releases_and_prune.md)에서 따라갈 수 있다.
