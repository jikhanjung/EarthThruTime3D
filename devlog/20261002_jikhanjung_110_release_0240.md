# v0.24.0 — 현재의 지구: 위성 영상 바탕에 바람·해류·구름

상태: 2026-10-02 운영 배포·공개 Chromium 검증 완료.

## 변경

- [#102](https://github.com/jikhanjung/EarthThruTime3D/pull/102) 현재(0 Ma)를 NASA Blue Marble 위성 영상으로
  보이고, ☰ 메뉴에 바람(10 m / 250 hPa)·해류·구름(위성 / 모형)을 더했다(jikhanjung P10·109). 바람·구름은 판을
  만들 때 받은 한 시각, 해류는 ECCO2 1992–2018 표층 평균이며, 켠 레이어의 시점이 연대 아래와 범례에 적힌다.
  wwolf 의 #89 검토(대칭 u·v 범위, `currents=flow`, ECCO2 조건의 출처)를 반영했다.

## 고정한 자료

- 바람·구름 시각: **2026-10-01 18:00 UTC**(GFS 분석 f000, 같은 시의 GMGSI). 판 PR 을 만든 2026-10-02 00:01 UTC 에는
  00 UTC 주기가 아직 올라오지 않아 18 UTC 가 가장 새것이었다. `sources/present_weather.json` 에 받은 주소·sha256.
- 새 자료 묶음 디렉터리 `present-earth/`: 카탈로그와 파일 7 개, 약 7.2 MB. 나머지 자료는 v0.23.0 과 같다.

## 빌드·운영 배포

- 깨끗한 main `d233d46`(#102·#103 병합)에서 개발 호스트가 `build.sh v0.24.0` 으로 빌드했다. Django 92 개, 패킹,
  이미지 스모크 통과.
- 자료 **1,297 개, 490,063,522 bytes**. v0.23.0 대비 `present-earth/` 8 개(카탈로그 + 7, 7,064,474 bytes)가 늘었고
  나머지는 같다. 호스트 묶음 파일은 설치된 것과 바이트까지 같아 풀지 않았다.
- 이미지 digest: `sha256:ccd4276b104eeaa7112366b2666eba4b1092715b30cfb6580486bfbfa079c322`. Docker Hub 에 push 하고
  dolfinid-2 에서 digest 로 pull 했다. 자료·호스트 아카이브는 scp 후 SHA-256 대조.
- 배포 전 dolfinid-2: v0.23.0 healthy, 디스크 여유 32 GB(배포 뒤 31 GB).
- `deploy.sh v0.24.0` 이 자료 1,297 개 검증 → DB 백업 `db-20261002T000520Z.sqlite3` → 컨테이너 교체 → 스모크를
  마쳤다. `.env.django` 배포 전후 동일, 운영 DB 유지, 컨테이너 healthy.
- 공개 `/healthz`: `ok`, `0.24.0`, PaleoAtlas 필수 90 개·누락 0.
- 공개 사이트에 `tests/flux-browser.mjs` 를 돌려 통과: 0 Ma 위성 바탕, 바람·해류·구름, 시점 줄과 범례, 0 Ma 밖에서
  꺼짐, 몰바이데, 주소, 영어, 휴대폰, **제3자 요청 0 건**. 공개 `/present/assets/mean-a583f1ad2244.png` 를 내려받아
  빌드 묶음과 sha256 이 같음을 확인했다.
- 롤백: `bash /srv/earththrutime3d/deploy.sh v0.23.0` (DB 복원 없음). v0.22.0 도 남아 있다.
- 정리: 배포 뒤 `prune.sh`(KEEP=2)로 v0.22.0 을 지웠다(+906 MiB, 31.9 GiB 여유).
