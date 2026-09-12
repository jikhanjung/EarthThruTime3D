# EarthThruTime3D

고지리 자료를 바탕으로 지구 역사를 3D로 재구성하는 PaleoBytes 연구 프로젝트입니다.
첫 목표는 시대별 지표면 시각화이며, 이후 지각 이동·변형과 맨틀 대류로 확장합니다.

현재는 **Django 5.2 초기 웹 기반**입니다. Scotese 고지도 17장을 로컬 연구 자료로 수집했으며,
3D 뷰어와 보간·물리 엔진은 아직 없습니다.

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
```

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
원본은 `data/sources/scotese/`에 로컬 저장하며 Git과 웹 배포에서 제외합니다.
새 체크아웃에서는 `.venv/bin/python scripts/fetch_scotese.py`로 동일 자료를 받을 수 있습니다.
첫 개발 기록은 [devlog](devlog/20260912_001_project_initialization.md)에 있습니다.
이 프로젝트의 소프트웨어 라이선스는 아직 지정하지 않았습니다.
