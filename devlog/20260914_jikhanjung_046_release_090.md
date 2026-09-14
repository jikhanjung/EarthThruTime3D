# jikhanjung 046 — v0.9.0 배포와 문서 현행화

날짜: 2026-09-14

## 한 것

045에서 합친 PaleoDEM 스택(고도 격자, 지형 음영, 기온, 해수면, 빙하, 극관 수정)을
v0.9.0으로 배포했다.

### 자료 만들기

- `scripts/fetch_paleodem.py --manifest`로 `sources/{paleodem,paleotemp,sealevel,ice}.json`의
  자료를 받았다. 모두 고정된 크기와 SHA-256이 맞았다. 처리용 패키지(netCDF4, openpyxl, pyshp)는
  `uv pip install --python .venv/bin/python -r requirements-processing.txt`로 깔았다.
  이 venv에는 `pip`가 없다.
- 극관 수정(044)이 조각을 바꾸므로 `segment_paleoatlas.py --jobs 8`로 PaleoAtlas 90장을 다시
  분할하고 `atlas_motions.py`를 다시 돌렸다(89 간격, 1322쌍, 최고 1.44°/Myr).
- 고도 텍스처는 **1° 격자에서 2048×1024, 8비트**로 만들었다. 문서는 6분 격자에서 만든다고
  했지만, 6분 묶음에는 540 Ma 격자가 없어 `build_paleodem.py`가 멈췄다. 화면 문구도 이미
  "1° 격자 109장"이라 1°로 가고 `docs/globe-viewer.md`를 고쳤다.
- `paleodem_motions.py`(111 간격, 28 간격이 5 Myr 안의 다른 나이 지도를 빌림),
  `build_paleotemp.py`(100장), `build_sealevel.py`, `build_ice.py`(과거 빙하 46장)를 돌렸다.
  고도 시리즈 파생 자료는 모두 65 MB이고, 자료 묶음은 76 MB가 됐다.

### 문서 현행화

- 문의 페이지: 공개 문의 채널이 없다는 문구를 GitHub Issues로 안내하는 문구로 바꿨다.
- 소개 페이지: 저장소 링크, PaleoCoastlines 출처, 과거 빙하(043) 설명을 넣었다. "과거 빙하는
  그리지 않는다", "판 운동을 계산하지 않는다"는 옛 문구를 고쳤다.
- 개인정보 페이지: "로컬 개발 단계, 호스팅 미정"을 빼고 언어 쿠키(1년)와 접근 키 세션을 적었다.
- 고도 격자의 보간 안내: 040 이후 대륙이 판 회전을 빌려 움직이는데도 "판 운동을 계산한 것이
  아니다"라고 되어 있어 고쳤다.
- README, `docs/architecture.md`, `docs/operations.md`, AGENTS.md를 운영 중인 뷰어 기준으로
  고쳤다. README는 아직 "17장, 보간 없음"이었다.

## 확인

- `make check`, `make test` 51개, `npm test` 통과.
- 브라우저 검사: 첫 실행에서 300 Ma 텍스처가 처음 불릴 때 5초 대기를 넘겨 한 번 실패했고,
  다시 돌리자 전부 통과했다. 새로 받은 텍스처가 캐시에 없을 때의 시간 문제로 보인다.
- 빌드 검사와 서버 검사 모두 통과(90개 거리장, 판 모델 다섯, 원본 지도 미제공).
- 배포 뒤 공개 주소에서 `/healthz`가 0.9.0을 보고했다. `?masks=paleodem2018`, 300 Ma 고도
  텍스처와 빙하 텍스처가 200이고, 영어 문의 페이지에 Issues 링크가 있다.
- 이미지 ID `sha256:bd329462c0c8…`를 `deploy/README.md`에 기록했다.

## 남은 것

- 서버에 v0.8.8, v0.8.9 이미지가 남아 있다(여유 공간 약 9.6 GB).
- `scripts/compile_messages.py`는 msgfmt가 거부하는 중복 msgid를 받아들인다.
