# v0.24.1 — 현재의 지구 고침 릴리스

상태: 2026-10-02 운영 배포·공개 Chromium 검증 완료.

## 변경

- [#104](https://github.com/jikhanjung/EarthThruTime3D/pull/104) 기본 자료(PaleoAtlas 2016)에서도 0 Ma 가 위성 영상,
  바람·해류 입자가 드래그 뒤 깜박이지 않음([jikhanjung 111](20261002_jikhanjung_111_present_default_and_flicker.md)).
  코드만 바뀌었다. 자료 묶음은 v0.24.0 과 같다(바람·구름 시각 2026-10-01 18 UTC 그대로).

## 빌드·운영 배포

- main `55e58b8`(#104·#105)에서 `build.sh v0.24.1`. Django 92 개, 패킹(1,297 개, 490,063,522 bytes — v0.24.0 과 같다), 이미지 스모크 통과.
- 이미지 digest `sha256:f8caf588c617759704c960bdfcf401ae9ec1592088c81511f0b29a1fd74fb226`. Docker Hub push, dolfinid-2 에서 digest 로 pull.
  아카이브 scp 후 SHA-256 대조. 호스트 묶음은 설치된 것과 같아 풀지 않았다.
- `deploy.sh v0.24.1`: 묶음 검증 → DB 백업 `db-20261002T001830Z.sqlite3` → 교체 → 스모크. `.env.django` 전후 동일, healthy.
- 공개 사이트에 `tests/flux-browser.mjs` 통과 — 기본 자료의 위성 바탕·마스크 안내 숨김·드래그 뒤 빈 프레임 없음 포함.
- 정리: `prune.sh` 로 v0.23.0 을 지웠다(+907 MiB, 32 GiB 여유). v0.24.1 이 돌고 v0.24.0 이 롤백으로 남는다.
- 롤백: `bash /srv/earththrutime3d/deploy.sh v0.24.0`.
