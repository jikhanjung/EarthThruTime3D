# v0.24.2 — 바람·해류 꼬리 깜박임 고침 릴리스

상태: 2026-10-02 운영 배포·공개 Chromium 검증 완료.

## 변경

- [#106](https://github.com/jikhanjung/EarthThruTime3D/pull/106) 드래그 뒤 꼬리가 길고 짧게 번갈던 것
  ([jikhanjung 113](20261002_jikhanjung_113_flux_trail_fade.md)). 코드만 바뀌었다. 자료 묶음은 v0.24.0 과 같다.

## 빌드·운영 배포

- main `1bfd815`(#106·#107)에서 `build.sh v0.24.2`. 자료 1,297 개(v0.24.0 과 같다), 이미지 스모크 통과.
- 이미지 digest `sha256:bc697bdd513109991d4aba1ac30d5c296acfca69542cb2fd65200fef752a2fe2`. Docker Hub push, digest 로 pull.
  아카이브 SHA-256 대조, 호스트 묶음 동일.
- `deploy.sh v0.24.2`: 묶음 검증 → DB 백업 `db-20261002T011710Z.sqlite3` → 교체 → 스모크. `.env.django` 전후 동일.
- 공개 사이트 `tests/flux-browser.mjs` 통과.
- 정리: `prune.sh` 로 v0.24.0 을 지웠다(+921 MiB, 32 GiB 여유). v0.24.2 가 돌고 v0.24.1 이 롤백으로 남는다.
