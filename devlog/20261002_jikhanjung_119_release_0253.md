# v0.25.3·v0.25.4 — 공개 사이트에서 접근 키와 비공개 판 모델, 쿠키 빼기 릴리스

상태: 릴리스 준비. 빌드·운영 배포 결과는 아래에 이어 적는다.

## 변경

- [#114](https://github.com/jikhanjung/EarthThruTime3D/pull/114) 사람이 "ACCESS_KEY 부분 공개된 사이트에선 제거해줘" 라고 했다.
  운영 `.env.django` 에서 `ACCESS_KEY` 를 빼고(배포 때), 이용 조건이 없는 `publish: false` 판 모델(Torsvik & Cocks 2017)을
  자료 묶음에서 뺀다. 개인정보·소개의 접근 키 문장은 키가 있는 실행 환경에서만, 소개의 판 인용은 내줄 수 있는 모델만.
  묶음은 v0.25.2 보다 `plates/torsvikcocks2017/` 만큼 작다.
- [#116](https://github.com/jikhanjung/EarthThruTime3D/pull/116)(v0.25.4) v0.25.3 을 공개 사이트에서 확인하다 첫 화면이 여전히
  `csrftoken` 쿠키를 심는 것을 찾았다. 판 안내의 숨긴 접근 키 양식이 키 없이도 `{% csrf_token %}` 과 함께 그려졌다. 양식을
  키가 있을 때만 그리게 했다 — 개인정보 쪽의 "다른 쿠키는 쓰지 않습니다" 가 그래야 사실이다.
