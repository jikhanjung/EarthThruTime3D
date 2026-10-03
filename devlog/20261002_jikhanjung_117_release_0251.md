# v0.25.1 — 소개 쪽의 출처·기여자, 하단 메뉴 정리 릴리스

상태: 2026-10-02 운영 배포·공개 검증 완료.

## 변경

- [#110](https://github.com/jikhanjung/EarthThruTime3D/pull/110) `/about/` 에 현재 지구 자료의 출처(NASA Blue Marble·GIBS,
  NOAA GFS, NOAA/NESDIS GMGSI, ECCO2)와 기여자 절, 하단 메뉴에서 맨틀 모형 실험 링크를 뺐다. README 를 영문으로 하고
  한국어판(`README.ko.md`)을 잇고, 사이트맵·설계·AGENTS·운영 문서를 P10·P11 에 맞췄다. 코드와 자료 묶음은 그대로다.

## 빌드·운영 배포

- main `d33c967`(#110·#111)에서 `build.sh v0.25.1`. Django 96 개, 자료 1,297 개(그대로), 이미지 스모크 통과.
- 이미지 digest `sha256:bd018eb26fadfd3ce072bfc78717876eb2d1cde22d27a2aa5aa05f13862c67ee`. Docker Hub push, digest 로 pull.
  아카이브 SHA-256 대조, 호스트 묶음 동일.
- `deploy.sh v0.25.1`: 묶음 검증 → DB 백업 `db-20261002T132525Z.sqlite3` → 교체 → 스모크. `.env.django` 전후 동일.
  컨테이너가 `scripts/` 를 v0.25.1 로 다시 깔았고(`INSTALLED`), crontab 그대로.
- 공개: `/healthz` ok 0.25.1, `present.source = release`(첫 자동 받기 전). `/about/` 에 Menemenlis·WWolf·기여자, 하단 메뉴에
  맨틀 링크 없음. `tests/flux-browser.mjs` 통과.
- 정리: `prune.sh` 로 v0.24.2 를 지웠다(+921 MiB, 32 GiB 여유). v0.25.1 이 돌고 v0.25.0 이 롤백으로 남는다.
