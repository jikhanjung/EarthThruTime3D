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

- [jikhanjung P04 — 메인 globe에 맨틀과 인도–아시아 단면 통합](20260915_jikhanjung_P04_globe_mantle_section_integration.md)
- [jikhanjung P03 — 지각 변형과 맨틀 대류 연결](20260915_jikhanjung_P03_crustal_deformation_mantle_coupling.md)
- [jikhanjung P02 — 시간 범위: 마지막 빙기 한 주기 (13만 년)](20260915_jikhanjung_P02_last_glacial_cycle.md)
- [jikhanjung P01 — 시간 범위 선택: 최근 2.5만 년](20260915_jikhanjung_P01_deglacial_time_window.md)

## 작업 기록

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

## 현재 상태 — v0.10.3 (2026-09-15)

2002년 Scotese 웹 지도 17장 수집과 구면 변환에서 시작해(001–002), 육지 분할·이름표·
시대 사이 보간을 추가했습니다(003–010). 지금 기본 자료는 2016년 PaleoAtlas 90장으로,
750 Ma부터 현재까지를 보여 줍니다. 기존 17장은 비교용으로 남아 있습니다.

판 회전 모델을 여러 개 읽어 대륙 윤곽을 재구성하며, PaleoAtlas 조각은 우세 판의 회전으로
중심점을 옮깁니다. 다만 화면에서는 그 주변을 이동시키고 모양을 섞는 근사 방식이므로,
조각 전체의 정확한 강체 회전이나 판 내부 변형 계산과는 구분합니다. 모델 간 경도 차이는
[경도 고정 문서](../docs/palaeolongitude.md)에 정리했습니다.

고도 격자 시리즈는 PaleoDEM 109장과 그보다 오래된 아틀라스 지도 3장으로 구성됩니다.
지형 음영·기온·해수면·빙하를 표시하고, 확대하면 고도 격자를 3D 지형으로 보여 줍니다.
마지막 빙하기 후퇴 시기에는 NADI-1·DATED-1 자료에서 만든 6–24 ka의 저수위 조각 18장을
사용합니다(jikhanjung 060). 지구본·몰바이데·정거원통 투영, 한영 전환, 모바일 조작을 지원합니다.

운영 서비스는 dolfinid에서 실행합니다. 원본 지도 이미지는 배포하지 않으며, 파생 자료의
서로 다른 이용 조건은 [LICENSE-DATA.md](../LICENSE-DATA.md)를 따릅니다. 배포 전·매시간 DB
스냅샷과 원격지 백업, 원본 미러 및 파생 자료의 단계별 스냅샷이 구성돼 있습니다.
운영 절차와 남은 점검 항목은 [운영 문서](../docs/operations.md)가 기준입니다.

## 남은 것

- **지각 변형:** 현재의 판 회전 기반 근사 보간을 개선하고, 충돌·단축·지각 두께·융기를
  명시적으로 다루는 모델이 필요합니다. 히말라야 생성과 맨틀 대류 솔버는 아직 없습니다.
- **시간 해상도:** 뷰어의 고정 시간 간격은 최소 0.5 Ma이며, 1만 년 tick은 미지원입니다.
  시간 간격을 줄이는 작업과 과학적 정확도 검증은 별개입니다.
- **자료 검증:** 2002년 지도 분할의 한계는 해당 비교 자료에 남아 있습니다. 모델 간 기준틀,
  해안선·고도·빙하의 불확실성과 보간 중 형상 변화도 계속 검증해야 합니다.
- **운영:** DB 복구 리허설, 디스크 감시와 백업 실패 알림이 남아 있습니다. 원격지 백업 자체는
  구현됐습니다. 상세 상태는 [docs/operations.md](../docs/operations.md)를 참고하세요.

개별 devlog는 당시 판단과 검증의 기록으로 보존합니다. 현재 기능 비교와 다음 단계는
[GPlates 비교 문서](../docs/gplates-reference.md), 뷰어 구현은
[docs/globe-viewer.md](../docs/globe-viewer.md)를 기준으로 읽으세요.
