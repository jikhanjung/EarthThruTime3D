# v0.24.0 — 현재의 지구: 위성 영상 바탕에 바람·해류·구름

상태: 릴리스 준비. 빌드·운영 배포 결과는 아래에 이어 적는다.

## 변경

- [#102](https://github.com/jikhanjung/EarthThruTime3D/pull/102) 현재(0 Ma)를 NASA Blue Marble 위성 영상으로
  보이고, ☰ 메뉴에 바람(10 m / 250 hPa)·해류·구름(위성 / 모형)을 더했다(jikhanjung P10·109). 바람·구름은 판을
  만들 때 받은 한 시각, 해류는 ECCO2 1992–2018 표층 평균이며, 켠 레이어의 시점이 연대 아래와 범례에 적힌다.
  wwolf 의 #89 검토(대칭 u·v 범위, `currents=flow`, ECCO2 조건의 출처)를 반영했다.

## 고정한 자료

- 바람·구름 시각: **2026-10-01 18:00 UTC**(GFS 분석 f000, 같은 시의 GMGSI). 판 PR 을 만든 2026-10-02 00:01 UTC 에는
  00 UTC 주기가 아직 올라오지 않아 18 UTC 가 가장 새것이었다. `sources/present_weather.json` 에 받은 주소·sha256.
- 새 자료 묶음 디렉터리 `present-earth/`: 카탈로그와 파일 7 개, 약 7.2 MB. 나머지 자료는 v0.23.0 과 같다.
