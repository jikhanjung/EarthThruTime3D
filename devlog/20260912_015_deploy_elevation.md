# 015 — 고도 시리즈를 운영 번들에 싣기

날짜: 2026-09-12 · 브랜치: feature/paleodem-deploy (014 위에 쌓음) · 버전: 0.3.3

## 문제

014의 뷰어는 PaleoDEM 텍스처가 전부 있을 때만 고도 시리즈를 켜고, 없으면 Scotese로
물러난다. 운영 번들(`deploy/pack_data.py`)은 거리장 17장과 조각 보고서만 싸므로, 그대로
배포하면 운영은 계속 Scotese 시리즈를 보여 준다. smoke도 `expected == 17`을 고정했다.

## 한 일

- 패커가 `sources/paleodem-slices.json`의 109장 텍스처(`paleodem-<age×10>-field.png`)를
  함께 싼다. 650 Ma 시점은 이미 싸던 Scotese 거리장이다. 하나라도 없으면 빌드가 멈춘다.
  번들은 약 93 MB가 된다.
- 이미지 smoke와 호스트 smoke가 `/healthz`의 `series == "paleodem"`, `expected == 110`,
  `missing == 0`을 요구한다. 홈에 Zenodo 출처가 있고, 650 Ma와 0 Ma 필드가 서비스되는지 본다.
  대륙 마스크 토글은 고도 시리즈에서 정당하므로 그 금지 검사는 뺐다.
- `.env.django.example`에 `GLOBE_SERIES=paleodem`을 명시했다. 텍스처 없는 번들은 자동으로
  Scotese로 물러나므로 롤백(v0.3.2)은 그대로 동작한다.
- 버전 0.3.3. 정적 파일 캐시 무효화(`?v=`)에도 필요하다. 뷰어 스크립트가 크게 바뀌었다.

## 확인

`pack_data.py v0.3.3`로 번들 생성, manifest 파일 수 확인. `make check`, Django 테스트.
`deploy/build.sh v0.3.3`(이미지 빌드 + smoke)는 Docker가 있는 호스트에서 실행한다.

## 남은 것

실제 배포는 `deploy/README.md` 절차대로 dolfinid에서 수행한다. 원격지 백업·복구 리허설(012)은
그대로 남아 있다.
