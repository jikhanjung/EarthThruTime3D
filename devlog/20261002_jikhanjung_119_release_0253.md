# v0.25.3 — 공개 사이트에서 접근 키와 비공개 판 모델 빼기 릴리스

상태: 릴리스 준비. 빌드·운영 배포 결과는 아래에 이어 적는다.

## 변경

- [#114](https://github.com/jikhanjung/EarthThruTime3D/pull/114) 사람이 "ACCESS_KEY 부분 공개된 사이트에선 제거해줘" 라고 했다.
  운영 `.env.django` 에서 `ACCESS_KEY` 를 빼고(배포 때), 이용 조건이 없는 `publish: false` 판 모델(Torsvik & Cocks 2017)을
  자료 묶음에서 뺀다. 개인정보·소개의 접근 키 문장은 키가 있는 실행 환경에서만, 소개의 판 인용은 내줄 수 있는 모델만.
  묶음은 v0.25.2 보다 `plates/torsvikcocks2017/` 만큼 작다.
