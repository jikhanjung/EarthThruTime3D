# EarthThruTime3D

고지리 자료를 바탕으로 지구 역사를 3D로 재구성하는 PaleoBytes 연구 프로젝트입니다.
첫 목표는 시대별 지표면 시각화이며, 이후 지각 이동·변형과 맨틀 대류로 확장합니다.

현재는 **Django 5.2 + Three.js 고지리 지구본 뷰어**입니다. Scotese 고지도 17장을
회전·확대하고 시대별로 탐색할 수 있습니다. 보간·물리 엔진은 아직 없습니다.

## 로컬 실행

Python 3.11 이상을 사용합니다. `.venv`는 이 저장소 전용 환경입니다.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
mkdir -p data/db
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver
```

uv를 사용한다면 설치 명령은 `uv pip install --python .venv/bin/python -r requirements.txt`입니다.
이미 초기화된 현재 작업 폴더에서는 마지막 `runserver` 명령만 실행하면 됩니다.

- 홈: http://127.0.0.1:8000/
- 소개: `/about/`, 개인정보: `/privacy/`, 문의: `/contact/`
- 상태: `/healthz` (버전·DB·마이그레이션 기록 확인)
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

홈에서 드래그로 회전하고 휠·핀치로 확대합니다. 시대 선택 메뉴 또는 타임라인으로
17개 시점을 바꿀 수 있습니다. 자동 회전·격자·시대 순서 재생·시점 초기화를 지원합니다.
지구본에 키보드 포커스를 두면 방향키로 회전, `+`/`-`로 확대·축소합니다.

지도는 Mollweide 투영을 가정한 **근사 변환**이며, 원본의 지명·경계선이 남아 있습니다.
고도나 지각 운동을 계산하지 않습니다. 원본 투영법과 중앙경선은 아직 확정되지 않았습니다.
[변환 구현과 한계](docs/globe-viewer.md)를 참고하세요.

Three.js 0.186.0과 MIT 라이선스는 `static/vendor/three/`에 포함됩니다.
일반 실행에는 npm이나 외부 CDN이 필요하지 않습니다. 라이브러리를 갱신할 때
`npm ci && npm run vendor`로 파일을 동기화합니다.

## 구성

- `config/settings/`: 공통·개발·운영 설정. manage.py 기본은 개발, WSGI/ASGI 기본은 운영.
- `core/`, `templates/`, `static/`: 공통 페이지, 관리자 접근 제한, 상태 점검.
- `config/version.py`: 앱 이름·브랜드·버전·릴리스 날짜 단일 정의.
- `data/db/`: Git에서 제외되는 로컬 SQLite 데이터. `media/`도 제외.
- [설계 방향](docs/architecture.md), [운영 준비 사항](docs/operations.md).

운영 설정은 환경변수를 사용합니다. `.env.example`은 참고용이며 자동으로 읽지 않습니다.
운영에는 명시적인 비밀키·호스트·영속 DB 경로가 필요합니다. 운영 배포 자동화는 아직 없습니다.
설정은 [Django 5.2 배포 체크리스트](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/)를 참고합니다.

## 공통 가이드

`.guides -> ../devdocs/guides` 상대 심볼릭 링크로 참조하고 Git에서는 제외합니다.
새 체크아웃에서는 형제 위치에 private devdocs가 있을 때 `ln -s ../devdocs/guides .guides`로 연결합니다.
가이드 원문은 복사·커밋하지 않습니다.

## 자료와 라이선스

[초기 자료 목록](sources/README.md)에 Scotese.com 고지도 17장의 출처·연대·검증 방법을 정리했습니다.
원본은 `data/sources/scotese/`에 로컬 저장하며 Git에서 제외합니다.
개발용 지구본은 목록에 등록된 JPEG만 제공합니다. 운영 설정에서는 기본 비활성화합니다.
새 체크아웃에서는 `.venv/bin/python scripts/fetch_scotese.py`로 동일 자료를 받을 수 있습니다.
첫 개발 기록은 [devlog](devlog/20260912_001_project_initialization.md)에 있습니다.
이 프로젝트의 소프트웨어 라이선스는 아직 지정하지 않았습니다.
