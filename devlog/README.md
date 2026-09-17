# devlog 인덱스

수행한 작업의 배경, 구현 판단, 확인 결과와 남은 한계를 기록합니다. 무엇이 관측이고
무엇이 해석이며 무엇이 작업자가 정한 값인지 각 기록에서 구분해 둡니다.

## 파일명 규칙

- 작업 결과: `YYYYMMDD_{author}_{nnn}_{title}.md` — 작성자마다 따로 올리는 번호
- 계획 문서: `YYYYMMDD_{author}_P{nn}_{title}.md` — 작성자마다 P01부터 별도 번호
- author는 GitHub 계정 이름의 소문자입니다(`jikhanjung`, `wwolf`).
- title은 영문 snake_case로 작성합니다.
- 다른 기록을 가리킬 때는 파일 링크나 "jikhanjung 046"처럼 작성자와 번호를 함께 씁니다.

작업자가 둘이 되어 2026-09-14부터 이 규칙을 씁니다. 같은 날 두 사람이 같은 다음 번호를
잡는 일이 없도록 번호를 작성자별로 나눴습니다. jikhanjung은 공용 번호의 다음인 046부터,
wwolf는 001부터 셉니다. 그 전의 001–045는 링크와 본문 속 번호 참조가 깨지지 않도록 이름을
바꾸지 않았고, 035–044는 WWolf가, 나머지는 jikhanjung이 작성했습니다.
`hanyang3d/devlog/`의 규칙을 따르되 번호는 이 저장소에서 독립적으로 부여합니다.
배포 절차는 [deploy/README.md](../deploy/README.md), 운영 현황은
[docs/operations.md](../docs/operations.md), 뷰어 구조는
[docs/globe-viewer.md](../docs/globe-viewer.md)에 있습니다.

## 계획

- [jikhanjung P07 — CRUST 2.0으로 현재 지구의 지각 두께 표시](20260916_jikhanjung_P07_crust2_visualization.md)
- [jikhanjung P06 — v0.11–v0.12 맨틀 통합 리뷰 후속 수정](20260915_jikhanjung_P06_mantle_integration_review_fixes.md)
- [jikhanjung P05 — 맨틀 근사 중첩부터 단면·시간 통합까지](20260915_jikhanjung_P05_globe_mantle_approximate_overlay.md)
- [jikhanjung P04 — 메인 globe에 맨틀과 인도–아시아 단면 통합](20260915_jikhanjung_P04_globe_mantle_section_integration.md)
- [jikhanjung P03 — 지각 변형과 맨틀 대류 연결](20260915_jikhanjung_P03_crustal_deformation_mantle_coupling.md)
- [jikhanjung P02 — 시간 범위: 마지막 빙기 한 주기 (13만 년)](20260915_jikhanjung_P02_last_glacial_cycle.md)
- [jikhanjung P01 — 시간 범위 선택: 최근 2.5만 년](20260915_jikhanjung_P01_deglacial_time_window.md)

## 작업 기록

- [jikhanjung 093 — OPT1 GPU 재현 계획 1차 검토](20260917_jikhanjung_093_opt1_gpu_roadmap_review.md)
- [jikhanjung 092 — v0.16.0 CRUST 2.0 지각 표시 릴리스](20260916_jikhanjung_092_release_0160.md)
- [jikhanjung 091 — CRUST 2.0 현재 지각 표시](20260916_jikhanjung_091_crust2_visualization.md)
- [wwolf 012 — PR #56 검토 후속: 경로 탐색·호수의 섬·캐시 키](20260916_wwolf_012_present_water_review_fixes.md)
- [wwolf 011 — 현재 격자는 오늘의 강과 호수를 따른다: Natural Earth와 HydroLAKES](20260916_wwolf_011_present_water.md)

- [jikhanjung 089 — v0.15.1 맨틀 JS 모듈 분리 릴리스](20260916_jikhanjung_089_release_0151.md)
- [jikhanjung 088 — 맨틀 JS 정리와 화면·렌더링 모듈 분리](20260916_jikhanjung_088_mantle_js_modules.md)

- [jikhanjung 087 — 배포 후 P06 재검토와 기록 점검](20260916_jikhanjung_087_p06_deployed_review.md)

- [jikhanjung 086 — v0.15.0 호수·자료 검증·Firefox 릴리스](20260916_jikhanjung_086_release_0150.md)

- [jikhanjung 085 — 호수 RGB 전환의 캐시와 자료 형식 보완](20260916_jikhanjung_085_lake_rgb_release_checks.md)

- [wwolf 010 — 호수 깊이를 두 번째 채널로: 넘치기 전에 고이는 물](20260915_wwolf_010_lake_depth.md)
- [jikhanjung 084 — Firefox BiDi 검사 실패 처리와 Linux 실행](20260916_jikhanjung_084_firefox_bidi_review_fixes.md)

- [wwolf 009 — Firefox 검사를 저장소에: WebDriver BiDi로 데스크톱 Firefox 구동](20260915_wwolf_009_firefox_check.md)
- [jikhanjung 083 — Zenodo 메타데이터와 고정 빌드 입력 분리](20260916_jikhanjung_083_zenodo_metadata_build_input.md)

- [jikhanjung 082 — Firefox·호수 PR과 Zenodo 검증 이슈 검토](20260916_jikhanjung_082_firefox_lakes_source_review.md)

- [jikhanjung 081 — v0.14.1 맨틀 표시 기본값 배포](20260916_jikhanjung_081_release_0141.md)

- [jikhanjung 080 — 맨틀 중첩 기본값: 절개 끄기·불투명도 70%](20260916_jikhanjung_080_mantle_overlay_defaults.md)

- [jikhanjung 079 — v0.14.0 PaleoMIST 빙하 하천 릴리스](20260916_jikhanjung_079_release_0140.md)

- [jikhanjung 078 — OPT1 출력 시간 간격과 재계산 가능성 조사](20260916_jikhanjung_078_mantle_output_resolution_research.md)

- [jikhanjung 077 — PaleoMIST 하천 PR 검토와 무결성 보완](20260916_jikhanjung_077_ice_rivers_review.md)

- [jikhanjung 076 — 연대 전환 중 지각·맨틀 화면 유지](20260916_jikhanjung_076_mantle_age_transition.md)

- [jikhanjung 075 — v0.13.0 하천·맨틀 리뷰 수정 릴리스](20260916_jikhanjung_075_release_0130.md)

- [jikhanjung 074 — 맨틀 통합 리뷰 후속 수정](20260916_jikhanjung_074_mantle_review_fixes.md)

- [jikhanjung 073 — 하천 PR 검토와 위도 경계 수정](20260916_jikhanjung_073_river_review_fixes.md)

- [wwolf 008 — 빙하기의 얼음 위로 흘린 하천: PaleoMIST 1.0](20260915_wwolf_008_ice_rivers.md)
- [wwolf 007 — 하천 층: 격자 위로 물을 흘린 잠재 배수망](20260915_wwolf_007_river_layer.md)
- [jikhanjung 072 — v0.12.0 맨틀 통합 릴리스](20260915_jikhanjung_072_release_0120.md)
- [jikhanjung 071 — 전 지구 맨틀·핵 표시와 시간·단면 연결](20260915_jikhanjung_071_globe_mantle_time_section.md)
- [jikhanjung 070 — 80 Ma 메인 globe 맨틀 근사 중첩](20260915_jikhanjung_070_globe_mantle_overlay.md)
- [jikhanjung 069 — OPT1·Müller·PALEOMAP 좌표계 정합 검사](20260915_jikhanjung_069_mantle_frame_alignment.md)
- [jikhanjung 068 — v0.11.0: 맨틀과 인도–아시아 단면 릴리스](20260915_jikhanjung_068_release_0110.md)
- [jikhanjung 067 — 인도–아시아 A–A′ 팝업과 3D 지표](20260915_jikhanjung_067_india_asia_section.md)
- [jikhanjung 066 — 지각 변형 자료 목록과 맨틀 3D 표면 실험](20260915_jikhanjung_066_mantle_source_preview.md)
- [jikhanjung 065 — v0.10.5: 최근 13만 년 시간 범위](20260915_jikhanjung_065_release_0105.md)
- [jikhanjung 064 — 시간 범위: 최근 13만 년](20260915_jikhanjung_064_last_glacial_cycle.md)
- [jikhanjung 063 — v0.10.4: 최근 2.5만 년 시간 범위](20260915_jikhanjung_063_release_0104.md)
- [jikhanjung 062 — 시간 범위: 최근 2.5만 년](20260915_jikhanjung_062_deglacial_time_window.md)
- [jikhanjung 061 — 현재 구현에 맞춘 문서 정리](20260915_jikhanjung_061_documentation_refresh.md)
- [jikhanjung 060 — v0.10.3: 빙하 구멍 메우기, 마지막 빙하기 물러남의 조각](20260915_jikhanjung_060_release_0103.md)
- [jikhanjung 059 — 터치 기울이기, 짧은 화면의 메뉴](20260915_jikhanjung_059_touch_tilt_short_menu.md)
- [jikhanjung 058 — v0.10.1: 휠 클릭으로 기울이기](20260914_jikhanjung_058_release_0101.md)
- [jikhanjung 057 — v0.10.0 배포와 NAS 백업](20260914_jikhanjung_057_release_0100.md)
- [jikhanjung 056 — 라이선스: 코드 MIT, 파생 자료 CC BY 4.0](20260914_jikhanjung_056_licence.md)
- [jikhanjung 055 — 오버레이 겹침 정리, 번역 파일 검사](20260914_jikhanjung_055_overlay_stacking.md)
- [jikhanjung 054 — 3D 지형의 기울기와 방향 조작](20260914_jikhanjung_054_terrain_tilt.md)
- [jikhanjung 053 — 선 레이어가 3D 지형을 따라간다](20260914_jikhanjung_053_lines_on_terrain.md)
- [wwolf 006 — 현재의 저수위를 마지막 빙하기 물러남의 복원으로](20260914_wwolf_006_deglacial_slices.md)
- [wwolf 005 — 빙하 마스크의 구멍 메우기와 두 방향 흐림](20260914_wwolf_005_ice_holes_and_smoothing.md)
- [jikhanjung 052 — 도구 줄은 필수만, 나머지는 메뉴로](20260914_jikhanjung_052_settings_menu.md)
- [jikhanjung 051 — v0.9.4 배포](20260914_jikhanjung_051_release_094.md)
- [jikhanjung 050 — 확대하면 고도 격자를 3D로](20260914_jikhanjung_050_elevation_3d_relief.md)
- [wwolf 004 — 빙하가 해수면을 따라간다](20260914_wwolf_004_ice_follows_sealevel.md)
- [wwolf 003 — 해수면을 슬라이더로](20260914_wwolf_003_sealevel_slider.md)
- [wwolf 002 — 아틀라스가 얼음을 그리지 않은 곳에 논문의 한계선 덮개](20260914_wwolf_002_ice_limit_cap.md)
- [wwolf 001 — 6분 격자가 있으면 그것으로 텍스처를 만든다](20260914_wwolf_001_fine_grids_by_default.md)
- [jikhanjung 049 — 더 가까이 확대](20260914_jikhanjung_049_closer_zoom.md)
- [jikhanjung 048 — 지도 중심 화면](20260914_jikhanjung_048_map_first_layout.md)
- [jikhanjung 047 — 도구 막대의 표시 자료 선택, devlog 작성자별 번호](20260914_jikhanjung_047_dataset_picker.md)
- [jikhanjung 046 — v0.9.0 배포와 문서 현행화](20260914_jikhanjung_046_release_090.md)
- [045 — PaleoDEM 스택 합치기, 고도 텍스처 8비트 기본](20260914_045_paleodem_8bit_and_merge.md)
- [044 — 극을 둘러싼 다각형의 극관 채우기](20260913_044_polar_cap.md)
- [043 — 과거의 빙하](20260913_043_past_ice.md)
- [042 — 기온 색 범례](20260913_042_temperature_legend.md)
- [041 — 화석 해안선을 판 운동에 태우기](20260913_041_coastline_motion.md)
- [040 — 고도 격자에 대륙 이름과 판 운동을 빌려 오기](20260913_040_elevation_motions.md)
- [039 — 현재 빙하](20260913_039_holocene_ice.md)
- [038 — 해수면: 격자 안에 있는 것과 없는 것](20260913_038_sea_level.md)
- [037 — 지표 기온과 전 지구 평균 기온 띠](20260913_037_paleotemperature.md)
- [036 — 음영 기복과 식생 없는 육지색](20260913_036_relief_shading.md)
- [035 — PaleoDEM 고도 격자를 세 번째 마스크 소스로](20260913_035_paleodem_elevation.md)
- [034 — KO|EN 언어 전환](20260913_034_english.md)
- [033 — 오늘 배포와 정리](20260913_033_releases_and_prune.md)
- [032 — 헤더 한 줄로, 보간 시점은 그 나이의 시대로](20260913_032_header_and_period.md)
- [031 — 1 Myr 단위로 시간 흐르게](20260913_031_one_myr_spacing.md)
- [030 — 몰바이데와 정거원통 지도 돌리기](20260913_030_turn_flat_maps.md)
- [029 — 경계선 드롭다운 기본값 바로잡기](20260913_029_overlay_default.md)
- [028 — 해양 화석으로 지도 검사](20260913_028_fossil_check.md)
- [027 — 화석으로 고친 해안선 겹쳐 보기](20260913_027_fossil_coastlines.md)
- [026 — 다른 고지리 자료 모아서 검토](20260913_026_paleogeography_review.md)
- [025 — PALEOMAP 판으로 이름 붙이고 회전으로 옮기기](20260913_025_atlas_plate_motion.md)
- [024 — 2016 PaleoAtlas를 기본 마스크로](20260913_024_atlas_frames.md)
- [023 — 2016 PaleoAtlas로 육지 마스크 다시 만들기](20260913_023_paleoatlas_masks.md)
- [022 — Scotese 회전 모델로 경도 비교](20260913_022_paleomap_longitude.md)
- [021 — 경도 고정 문제 정리](20260913_021_palaeolongitude.md)
- [020 — 접근 키와 비공개 모델](20260913_020_access_key.md)
- [019 — 버튼을 드롭다운으로, 네 번째 모델](20260913_019_model_dropdown.md)
- [018 — 지도가 없는 시대까지](20260913_018_deep_time.md)
- [017 — 세 번째 모델과 오래된 버전 정리](20260913_017_third_model_and_prune.md)
- [016 — 판 모델을 여러 개 다루기](20260913_016_two_plate_models.md)
- [015 — 판 재구성 겹쳐 보기](20260913_015_plate_overlay.md)
- [014 — GPlates 회전 모델 들여오기](20260913_014_plate_rotation_model.md)
- [013 — 모바일은 뷰와 슬라이더 먼저](20260912_013_phone_layout.md)
- [012 — dolfinid 배포](20260912_012_deployment.md)
- [011 — 투영 방식 선택](20260912_011_projections.md)
- [010 — 이동 판정을 속도에서 정체성으로](20260912_010_motion_identity.md)
- [009 — 대륙이 이동하는 보간](20260912_009_continent_motion.md)
- [008 — 타임라인 샘플링 파라미터화](20260912_008_timeline_sampling.md)
- [007 — 패널 크기 고정](20260912_007_panel_sizing.md)
- [006 — 시점 사이 보간](20260912_006_interpolated_stops.md)
- [005 — 대륙 이름표](20260912_005_landmass_names.md)
- [004 — 마스크로 칠한 지구본](20260912_004_mask_surface.md)
- [003 — 지도에서 대륙 떼어내기](20260912_003_landmass_segmentation.md)
- [002 — Scotese 고지도 지구본 뷰어](20260912_002_reference_globe_viewer.md)
- [001 — 프로젝트 초기화 및 Scotese 고지도 수집](20260912_001_project_initialization.md)

## 현재 상태 — v0.16.0 (2026-09-16)

2002년 Scotese 웹 지도 17장 수집과 구면 변환에서 시작해(001–002), 육지 분할·이름표·
시대 사이 보간을 추가했습니다(003–010). 지금 기본 자료는 2016년 PaleoAtlas 90장으로,
750 Ma부터 현재까지를 보여 줍니다. 기존 17장은 비교용으로 남아 있습니다.

판 회전 모델을 여러 개 읽어 대륙 윤곽을 재구성하며, PaleoAtlas 조각은 우세 판의 회전으로
중심점을 옮깁니다. 다만 화면에서는 그 주변을 이동시키고 모양을 섞는 근사 방식이므로,
조각 전체의 정확한 강체 회전이나 판 내부 변형 계산과는 구분합니다. 모델 간 경도 차이는
[경도 고정 문서](../docs/palaeolongitude.md)에 정리했습니다.

고도 격자 시리즈는 PaleoDEM 109장과 그보다 오래된 아틀라스 지도 3장으로 구성됩니다.
지형 음영·기온·해수면·빙하를 표시하고, 확대하면 고도 격자를 3D 지형으로 보여 줍니다.
최근 2.5만 년과 마지막 빙기 한 주기(13만 년)를 별도 시간 창으로 볼 수 있습니다.
최근 범위의 빙하 조각과 더 오래된 시기의 해수면 대응 유사 자료를 구분합니다(062·064). 지구본·몰바이데·정거원통 투영, 한영 전환, 모바일 조작을 지원합니다.

메인 지구본에서 전 지구 맨틀·핵 참고 구를 켜고 지표 절개·불투명도를 조절할 수 있습니다.
80·60·40·20·0 Ma와 원본 OPT1 A–A′ 팝업은 시간을 공유합니다. 이는 서로 다른 복원
모델의 근사 중첩이며, 새 대류·변형 계산은 아닙니다(jikhanjung 070–072).
연대 전환 중 이전 지각·맨틀을 유지하고 준비된 자료를 함께 교체하며, 기본 절개는 Off,
지표 불투명도는 70%입니다(076·080). 독립 맨틀은 20 Ma 간격의 원본 51시점을 사용합니다.

잠재 하천 일반 109장·저수위 31장과 PaleoMIST 빙기 10장(2.5–25 ka)을 제공합니다.
v0.15.0의 빙기 호수는 웅덩이 계산에 따른 근사 결과이며 검증된 실제 호수 복원이 아닙니다.
RGB 자료 변환·재생성, 캐시 전환, Firefox 검사 및 배포 결과는 083–086에 기록했습니다.
v0.15.1에서는 맨틀 중첩 제어와 렌더링을 분리하고 모듈 캐시 호환성을 보완했습니다(088–089).

v0.16.0에서는 0 Ma의 CRUST 2.0 지각 두께 색상 지도와 설명용 절개층을 제공합니다(091–092).

운영 서비스는 dolfinid에서 실행합니다. 원본 지도 이미지는 배포하지 않으며, 파생 자료의
서로 다른 이용 조건은 [LICENSE-DATA.md](../LICENSE-DATA.md)를 따릅니다. 배포 전·매시간 DB
스냅샷과 원격지 백업, 원본 미러 및 파생 자료의 단계별 스냅샷이 구성돼 있습니다.
운영 절차와 남은 점검 항목은 [운영 문서](../docs/operations.md)가 기준입니다.

## 남은 것

CRUST 2.0 현재 지각 색상·두께 기준 구면층은 P07·091에서 구현하고 v0.16.0으로 운영 배포했다(092).
물·얼음과 기준 고도를 확정한 실제 모호면이나 과거 지각 변형 계산은 포함하지 않는다.

- **지각 변형:** 현재의 판 회전 기반 근사 보간을 개선하고, 충돌·단축·지각 두께·융기를
  명시적으로 다루는 모델이 필요합니다. 히말라야 생성과 맨틀 대류 솔버는 아직 없습니다.
- **시간 해상도:** 일반 지질 시대의 고정 간격은 최소 0.5 Ma, 최근 시간 창은 1 ka 표시 눈금입니다.
  이는 원자료의 시간 해상도나 정확도를 뜻하지 않습니다. OPT1의 5 Ma 공개 결과는 찾지 못했으며
  재계산의 입력·자원 제약은 078에 기록했습니다.
- **P06 후속:** PaleoDEM 파생 PNG의 기대 해시 manifest와 단면 빌더 입력 검증이 남아 있습니다.
  주요 결함은 v0.13.0부터 배포됐습니다. 맨틀 JS 정리·scene 분리·화면 연결 정리는 v0.15.1에 반영했습니다.
- **자료 검증:** 2002년 지도 분할의 한계는 해당 비교 자료에 남아 있습니다. 모델 간 기준틀,
  해안선·고도·빙하의 불확실성과 보간 중 형상 변화도 계속 검증해야 합니다.
- **운영:** DB 복구 리허설, 디스크 감시와 백업 실패 알림이 남아 있습니다. 원격지 백업 자체는
  구현됐습니다. 상세 상태는 [docs/operations.md](../docs/operations.md)를 참고하세요.

개별 devlog는 당시 판단과 검증의 기록으로 보존합니다. 현재 기능 비교와 다음 단계는
[GPlates 비교 문서](../docs/gplates-reference.md), 뷰어 구현은
[docs/globe-viewer.md](../docs/globe-viewer.md)를 기준으로 읽으세요.
