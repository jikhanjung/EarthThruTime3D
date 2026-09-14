# jikhanjung 056 — 라이선스: 코드 MIT, 파생 자료 CC BY 4.0

날짜: 2026-09-14 · 브랜치: chore/licence

## 한 것

프로젝트 라이선스를 정했다. 코드와 자료를 나눈다.

- `LICENSE`: 코드(Django 앱, 뷰어·처리 스크립트, 템플릿, 스타일, 검사)는 MIT. 저작권자는 브랜딩
  가이드대로 판매자인 PaleoBytes로 적고 괄호에 이름을 넣었다. `static/vendor/`의 Three.js는 자기
  MIT 고지를 따로 가진다.
- `LICENSE-DATA.md`: 자료는 세 묶음이다.
  - CC BY 원본에서 만든 파생 자료(고도·기온·빙하 텍스처, 해수면 곡선, 이동장, 해안선·판 자료,
    카탈로그와 주석)는 CC BY 4.0. 표기는 "EarthThruTime3D (PaleoBytes), derived from …"에 원본
    인용을 붙인다.
  - 원본 조건이 확정되지 않은 것: PaleoAtlas(2016) 마스크는 Zenodo 기록의 CC BY 표기를 누가 붙였는지
    확인하지 못해 그 기록의 조건대로 두고 별도 라이선스를 주장하지 않는다. 2002년판 마스크는
    PALEOMAP 이용 조건을 따른다. Torsvik & Cocks 2017은 라이선스가 없어 공개하지 않는다.
  - `data/sources/`의 원본 아카이브는 저장소에 없고 발행처 조건을 따른다.
- 소개 페이지, README, `docs/operations.md`(남은 항목에서 제거), `package.json`의 `license`를 맞췄다.

## 확인

- `make test` 51개 통과. 번역 파일 검사(055) 통과.
