# v0.25.3·v0.25.4 — 공개 사이트에서 접근 키와 비공개 판 모델, 쿠키 빼기 릴리스

상태: 2026-10-02 v0.25.3·v0.25.4 운영 배포·공개 검증 완료.

## 변경

- [#114](https://github.com/jikhanjung/EarthThruTime3D/pull/114) 사람이 "ACCESS_KEY 부분 공개된 사이트에선 제거해줘" 라고 했다.
  운영 `.env.django` 에서 `ACCESS_KEY` 를 빼고(배포 때), 이용 조건이 없는 `publish: false` 판 모델(Torsvik & Cocks 2017)을
  자료 묶음에서 뺀다. 개인정보·소개의 접근 키 문장은 키가 있는 실행 환경에서만, 소개의 판 인용은 내줄 수 있는 모델만.
  묶음은 v0.25.2 보다 `plates/torsvikcocks2017/` 만큼 작다.
- [#116](https://github.com/jikhanjung/EarthThruTime3D/pull/116)(v0.25.4) v0.25.3 을 공개 사이트에서 확인하다 첫 화면이 여전히
  `csrftoken` 쿠키를 심는 것을 찾았다. 판 안내의 숨긴 접근 키 양식이 키 없이도 `{% csrf_token %}` 과 함께 그려졌다. 양식을
  키가 있을 때만 그리게 했다 — 개인정보 쪽의 "다른 쿠키는 쓰지 않습니다" 가 그래야 사실이다.

## 빌드·운영 배포

- v0.25.3: main `88e1635`. 자료 **1,295 개, 489,665,330 bytes**(v0.25.2 에서 `plates/torsvikcocks2017/` 두 파일 빠짐).
  digest `sha256:3d162d0b01d8217bea28c55e3a765746f0612e39c80fa8b01f6ec4981289cf01`.
  운영 `.env.django` 를 `.env.django.before-0253`(600)으로 복사한 뒤 `ACCESS_KEY` 줄만 지웠다(다른 키 이름은 그대로,
  값은 출력하지 않았다). DB 백업 `db-20261002T135559Z.sqlite3`. 공개: 목록에 Torsvik 없음, 그 경로 404, Merdith 200.
  여기서 첫 화면의 `csrftoken` 쿠키를 찾아 v0.25.4 로 고쳤다.
- v0.25.4: main `19b30ec`. 자료 1,295 개 그대로. digest `sha256:884161f85b9705c3d291b7d371943acda321a7805d693a57a1e3dd6638118c88`.
  DB 백업 `db-20261002T140141Z.sqlite3`. `.env.django` 는 v0.25.3 때와 같다. 공개: `/`·`/about/`·`/privacy/`·
  `/?masks=paleodem2018` 모두 `Set-Cookie` 0 개, `/healthz` ok 0.25.4, `tests/flux-browser.mjs` 통과.
- 정리: 두 번의 `prune.sh` 로 v0.25.1·v0.25.2 를 지웠다. v0.25.4 가 돌고 v0.25.3 이 롤백으로 남는다. 키 없이 앞 판으로
  되돌려도 비공개 모델은 목록에 나오지 않는다(키가 없으면 내주지 않는 코드는 예전부터 같다).
