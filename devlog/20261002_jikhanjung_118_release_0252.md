# v0.25.2 — 운영에서 관리자 경로 빼기, 개인정보 안내 고침 릴리스

상태: 2026-10-02 운영 배포·공개 검증 완료.

## 변경

- [#112](https://github.com/jikhanjung/EarthThruTime3D/pull/112) 사람이 "about 에 Administrator accounts and login sessions 이게
  어딘가에 관리자 로긴이 있다는 말처럼 들리는데 그런 거 전혀 없잖아?" 라고 했다. 확인해 보니 운영에서 `/admin/login/` 이
  누구에게나 열려 있었고(200), 운영 DB 의 계정은 0 개였다. `ADMIN_ENABLED`(운영 기본 꺼짐)로 경로를 뺐고, `/privacy/`·
  `/about/` 의 안내를 실제대로 고쳤다: 회원 가입·로그인 없음, 쿠키는 언어(1 년)와 비공개 판 모델 접근 키(세션 30 일,
  CSRF)에만, 지구본 자료는 모두 이 서버에서. 자료 묶음은 그대로다.

## 빌드·운영 배포

- main `6103a68`(#112·#113)에서 `build.sh v0.25.2`. Django 97 개, 자료 1,297 개(그대로), 이미지 스모크 통과.
- 이미지 digest `sha256:f91b1b25b168e4c3c81d745d63d837d9335e0d95a650e6cd3ae3ca46db953ffa`. push, digest 로 pull, 아카이브 대조,
  호스트 묶음 동일. 운영 `.env.django` 에 `ADMIN_ENABLED` 없음(기본 꺼짐 그대로).
- `deploy.sh v0.25.2`: 묶음 검증 → DB 백업 `db-20261002T134434Z.sqlite3` → 교체 → 스모크. `.env.django` 전후 동일.
  컨테이너가 `scripts/` 를 v0.25.2 로 다시 깔았다.
- 공개: `/admin/`·`/admin/login/` 404, `/privacy/` 에 "회원 가입도 로그인도 없습니다", `/about/` 에 "관리자" 없음,
  `/healthz` ok 0.25.2, `tests/flux-browser.mjs` 통과.
- 정리: `prune.sh` 로 v0.25.0 을 지웠다(+921 MiB). v0.25.2 가 돌고 v0.25.1 이 롤백으로 남는다.
