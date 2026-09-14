# EarthThruTime3D

고지리 자료를 바탕으로 지구 역사를 3D로 재구성하는 PaleoBytes 연구 프로젝트입니다.
첫 목표는 시대별 지표면 시각화이며, 이후 지각 이동·변형과 맨틀 대류로 확장합니다.

현재는 **Django 5.2 + Three.js 고지리 지구본 뷰어**이며
https://earththrutime.nopeoplestime.info 에서 운영합니다.

- 기본 화면: PALEOMAP PaleoAtlas(2016) 지도 90장(750 Ma~현재)에서 분할한 육지 마스크.
  지도 사이는 조각을 PALEOMAP 판 회전으로 옮기며 모양을 섞는 보간입니다.
- 고도 격자 시리즈(`?masks=paleodem2018`): PaleoDEM(Scotese & Wright 2018) 109장에 지형 음영,
  지표 기온(Scotese 2021), 해수면 곡선(van der Meer 2022, Spratt & Lisiecki 2016), 빙하 층.
- 비교용 2002년판 웹 지도 17장(`?masks=scotese2002`).
- 판 회전 모델(Merdith 2021, Müller 2022, Cao 2024, Matthews 2016, PALEOMAP 2016) 경계선과
  PaleoCoastlines(Kocsis & Scotese 2021) 해안선 겹쳐 보기.
- 한국어/영어(KO|EN) 전환.

보간 화면과 해수면 가정 화면은 관측이나 발표된 복원이 아닙니다. 화면과 문서에서 원본 자료,
보간 결과, 가정 화면을 구분해 표시합니다. 문제 보고는
[GitHub Issues](https://github.com/jikhanjung/EarthThruTime3D/issues)에 남겨 주세요.

## 로컬 실행

Python 3.11 이상을 사용합니다. `.venv`는 이 저장소 전용 환경입니다.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
mkdir -p data/db
.venv/bin/python manage.py migrate
.venv/bin/python scripts/compile_messages.py   # 영어 번역 .mo 생성
.venv/bin/python manage.py runserver
```

uv를 사용한다면 설치 명령은 `uv pip install --python .venv/bin/python -r requirements.txt`입니다.
자료를 새로 만들 때는 `requirements-processing.txt`도 설치합니다.

- 홈: http://127.0.0.1:8000/
- 소개: `/about/`, 개인정보: `/privacy/`, 문의: `/contact/`
- 상태: `/healthz` (버전·DB·마이그레이션·거리장 확인)
- 관리자: `/admin/` (`.venv/bin/python manage.py createsuperuser`로 계정 생성)

```bash
make check
make test
npm ci
npm test
# 개발 서버를 실행한 상태에서 (필요시 npx playwright install chromium):
npm run test:browser
```

## 지구본 조작

홈에서 드래그로 회전하고 휠·핀치로 확대합니다. 지구본·몰바이데·정거원통 투영을 고를 수
있고, 평면 지도도 경도를 돌릴 수 있습니다. 시대 선택 메뉴, 타임라인 슬라이더, 시간 간격
(지도마다 몇 단계 또는 1 Myr) 선택, 시대 순서 재생, 자동 회전, 격자(기본 켬), 시점 초기화를
지원합니다. 지구본에 키보드 포커스를 두면 방향키로 회전, `+`/`-`로 확대·축소합니다.

변환 구현, 보간 방식과 한계는 [지구본 뷰어 문서](docs/globe-viewer.md), 고지자기 경도 문제는
[경도 고정 문서](docs/palaeolongitude.md)를 참고하세요.

Three.js 0.186.0과 MIT 라이선스는 `static/vendor/three/`에 포함됩니다.
일반 실행에는 npm이나 외부 CDN이 필요하지 않습니다. 라이브러리를 갱신할 때
`npm ci && npm run vendor`로 파일을 동기화합니다.

## 구성

- `config/settings/`: 공통·개발·운영 설정. manage.py 기본은 개발, WSGI/ASGI 기본은 운영.
- `core/`, `templates/`, `static/`: 페이지, 지구본 뷰어, 관리자 접근 제한, 상태 점검.
- `locale/`: 영어 번역(`django.po`). `.mo`는 `scripts/compile_messages.py`로 만들며 Git에서 제외.
- `scripts/`: 자료 받기·검증, 분할, 이동·고도·기온·해수면·빙하 파생 자료 생성.
- `sources/`, `annotations/`: 자료 출처 매니페스트와 사람이 붙인 주석.
- `config/version.py`: 앱 이름·브랜드·버전·릴리스 날짜 단일 정의.
- `deploy/`: 이미지·자료 묶음 빌드와 배포 스크립트. 절차는 [deploy/README.md](deploy/README.md).
- `data/`: Git에서 제외되는 원본·파생 자료와 로컬 SQLite. `media/`도 제외.
- [설계 방향](docs/architecture.md), [운영 현황](docs/operations.md), 작업 기록은 [devlog](devlog/README.md).

운영 설정은 환경변수를 사용합니다. `.env.example`은 참고용이며 자동으로 읽지 않습니다.
운영에는 명시적인 비밀키·호스트·영속 DB 경로가 필요합니다. 이미지는 개발 호스트에서 빌드하고
서버는 버전이 붙은 이미지와 자료 묶음을 검증한 뒤 교체만 합니다.
설정은 [Django 5.2 배포 체크리스트](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/)를 참고합니다.

## 공통 가이드

`.guides -> ../devdocs/guides` 상대 심볼릭 링크로 참조하고 Git에서는 제외합니다.
새 체크아웃에서는 형제 위치에 private devdocs가 있을 때 `ln -s ../devdocs/guides .guides`로 연결합니다.
가이드 원문은 복사·커밋하지 않습니다.

## 자료와 라이선스

[자료 목록](sources/README.md)에 각 자료의 출처·연대·라이선스·검증 방법을 정리했습니다.
원본은 `data/sources/`에 로컬 저장하며 Git에서 제외합니다. `scripts/fetch_scotese.py`,
`scripts/fetch_paleodem.py --manifest sources/<이름>.json` 등으로 고정된 SHA-256과 함께 받습니다.
PALEOMAP 원본 지도 이미지는 이용 조건을 확인하기 전까지 배포하지 않으며, 운영 이미지와 자료
묶음에도 넣지 않습니다. 이 프로젝트의 소프트웨어 라이선스는 아직 지정하지 않았습니다.
