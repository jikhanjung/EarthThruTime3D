# v0.25.2 — 운영에서 관리자 경로 빼기, 개인정보 안내 고침 릴리스

상태: 릴리스 준비. 빌드·운영 배포 결과는 아래에 이어 적는다.

## 변경

- [#112](https://github.com/jikhanjung/EarthThruTime3D/pull/112) 사람이 "about 에 Administrator accounts and login sessions 이게
  어딘가에 관리자 로긴이 있다는 말처럼 들리는데 그런 거 전혀 없잖아?" 라고 했다. 확인해 보니 운영에서 `/admin/login/` 이
  누구에게나 열려 있었고(200), 운영 DB 의 계정은 0 개였다. `ADMIN_ENABLED`(운영 기본 꺼짐)로 경로를 뺐고, `/privacy/`·
  `/about/` 의 안내를 실제대로 고쳤다: 회원 가입·로그인 없음, 쿠키는 언어(1 년)와 비공개 판 모델 접근 키(세션 30 일,
  CSRF)에만, 지구본 자료는 모두 이 서버에서. 자료 묶음은 그대로다.
