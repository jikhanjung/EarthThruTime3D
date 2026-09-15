# jikhanjung P06 — v0.11–v0.12 맨틀 통합 리뷰 후속 수정

날짜: 2026-09-15 · 기준: v0.12.0 (`7188364`) · 상태: 계획, 미착수

대상: [jikhanjung 066](20260915_jikhanjung_066_mantle_source_preview.md)–[072](20260915_jikhanjung_072_release_0120.md),
PR #33–#37 (`18f3964..7188364`, 75개 파일, 약 6,500줄 추가).

## 리뷰 방법과 전체 판단

백엔드·배포, 메인 지구본 맨틀 중첩 프런트엔드, 단면·맨틀 페이지와 처리 스크립트를
나누어 코드를 읽었다. `make check`, `make test`(Django 63개), `npm test`는 통과했다.
자동 실행에 빠진 `tests/mantle-overlay.test.mjs`, `tests/collision.test.mjs`와
`tests/{geodynamics,india_asia,frame_alignment}_check.py`도 따로 실행해 통과했다.
브라우저 화면은 이번 리뷰에서 다시 확인하지 않았다.

다음 사항은 문제가 없음을 확인했다. 아래 수정 과정에서 이 성질을 깨지 않는다.

- 좌표 변환: 축 변환 `(x,z,−y)`, Kabsch 회전(반사 방지 포함), 사원수 순서,
  단면 법선 `(−sin, cos, 0)`과 반평면, `NonDimDepth·6371` 깊이, 지각 평형식.
- 출처: OPT1은 CC BY 4.0이며 `/mantle/`과 지구본 중첩에 출처·라이선스를 표시한다.
  원본 관측, 보간 기하, 시뮬레이션 결과, 참고용 핵 구가 구분되어 표시된다.
- 파일 제공: 파일명 정규식 → 카탈로그 항목 → `resolve()`·`is_relative_to` 순으로 경로를
  제한하고, 크기·SHA-256이 다르면 404를 준다. 해시 URL은 `immutable`로 캐시한다.
- 경합·자원: 요청마다 AbortController를 쓰고 늦게 도착한 결과를 버린다. 새 메시가
  준비된 뒤에 이전 메시를 해제한다. 지구본↔팝업 시간 동기화는 사용자 `input`에만
  메시지를 보내므로 서로 반복 호출하지 않는다.
- 배포 안전 규칙: `.env.django`와 운영 DB를 쓰지 않는다. `.env`는 임시 파일에서 만들고
  `docker compose config`로 검증한 뒤 교체한다. 이제 healthcheck·스모크 실패도 롤백
  조건에 들어간다.
- 번역: 새 한국어 문자열에 모두 영어 번역이 있고 fuzzy 항목이 없다.

## 1단계 — 장애와 표시 결함 (우선)

### 1-1. 맨틀 카탈로그 오류가 홈 전체를 500으로 만든다

- `core/globe.py:806-809`은 `/`를 렌더링할 때마다 `globe_overlay()`를 부른다.
  `core/mantle.py:22-31`의 `catalogue()`는 `schema_version`·`source`가 다르면
  `ValueError`를 던지고, JSON 파싱 오류나 `frames`·`layers` 키 누락도 잡지 않는다.
  `globe_overlay()`(`core/mantle.py:106`)도 예외를 잡지 않는다.
- 결과: 런타임 자료가 어긋나면 중첩만 빠지는 대신 홈이 500이 된다. 함수 설명의
  "fail closed"와 다르다. `/healthz`는 맨틀 자료를 보지 않아 이 상태에서도 통과한다.
- `core/collision.py`의 `catalogue()`도 같다. 단면 페이지가 "자료 준비 안 됨" 대신 500이 된다.
- 수정: 중첩 계산에서 카탈로그·설정 예외를 잡아 기록하고 `None`을 반환한다. 단면 페이지도
  준비 안 됨 화면으로 보낸다. 잘못된 카탈로그로 `/`와 `/collision/`을 요청해 200과
  "중첩 없음"을 확인하는 테스트를 추가한다. 현재 `test_mantle_overlay`는 `catalogue`를
  패치해 함수만 호출하므로 이 경로를 검사하지 못한다.

### 1-2. 확대 시 해안선·판 경계선이 지표 아래로 파묻힐 수 있다 (화면 확인 필요)

- 071에서 구면 선을 `normalize(position) * (terrainLift + surfaceLineLift)`로 바꾸며
  고정 여유 0.007(약 45 km)을 없앴다(`static/core/globe.js:983`). 확대 시 여유는
  `globe.js:1273`에서 구면 메시 해상도로 정해져 약 3.8e-5다.
- 선분은 두 꼭짓점 사이의 현이다. 길이 d(라디안)인 현의 가운데는 구면에서 약 d²/8
  아래에 있다. `coastlines-005.json`의 선분 2,632개 중 837개가 1°를 넘고, 상위 10%인
  1.8° 선분만 해도 약 1.3e-4 처진다. 판 경계선도 같다.
- 3D 지형 ×5·×20에서는 선 높이를 꼭짓점에서만 구하고 사이 지형은 보간되므로, 해안
  근처에서 지면이 선보다 1e-4–6e-4 높을 수 있다.
- 071의 확인은 한 장면 스크린샷이었다. 먼저 확대 + 지형 과장 끔/×5/×20에서 해안선·판
  경계를 실제로 캡처해 문제 여부를 확인한다. 평면 투영은 기존 여유를 유지해 해당 없음.
- 수정 후보: 선분 길이에 맞춘 여유(`(최대 선분 길이)²/8`를 더함), 긴 선분 세분화, 또는
  `polygonOffset`. 지표에서 떠 보이던 원래 문제(071)가 되살아나지 않는지 같이 확인한다.

### 1-3. 중첩 중 지표 로딩이 실패하면 지표가 계속 숨겨진다

- `selectStop(..., overlayManaged=true)`가 `globe.js:317`에서 `surfaceMesh`를 숨기고
  성공 시 `globe.js:448`에서만 다시 보인다. 실패 경로에서는 복원하지 않는다.
- `mantle-overlay.js`의 오류 처리는 절개·불투명도만 초기화하고 지표 표시는 건드리지 않는다.
- 수정: 실패 시 이전 지표를 다시 보이거나 오류 상태를 명확히 표시한다. 브라우저 검사의
  실패/재시도 시나리오에 지표 표시 여부를 추가한다.

## 2단계 — 검사 연결과 배포 스크립트

### 2-1. 새 JS 테스트가 `npm test`에 없다

- `package.json:8`은 `projection`·`rotation` 테스트만 실행한다.
  `tests/mantle-overlay.test.mjs`, `tests/collision.test.mjs`를 추가한다. 추가 의존성은 없다.
- `tests/*_check.py`는 원본 자료가 필요한 처리 검사이므로 기존 `ice_check`처럼 수동 실행을
  유지하되, 실행 명령을 `docs/geodynamics.md` 또는 해당 문서에 모아 둔다.

### 2-2. 스모크가 `.env`의 포트를 읽지 않는다 (잠재)

- `deploy/host/update_compose_env.py:17-20`은 기존 `.env`의 `HOST_PORT`를 유지한다.
  `deploy/host/smoke.sh:6`은 셸의 `${HOST_PORT:-8014}`만 쓴다.
- 두 값이 다르면 스모크가 다른 포트를 검사해 실패하고, 이제 롤백까지 실행된다.
  예전 `printf`는 항상 셸 값을 기록해 둘이 일치했다. 운영은 8014라 아직 드러나지 않았다.
- 수정: `smoke.sh`가 `IMAGE_TAG`처럼 `.env`에서 `HOST_PORT`를 읽는다.

### 2-3. `deploy/pack_data.py`의 검사 순서와 gzip 처리

- `pack_data.py:51`이 경로 안전 검사(63행)보다 먼저 `document['file']`을 읽는다.
- `pack_data.py:59`는 `gzip`이 없는 항목에서 `KeyError`가 나지만 서버의 자산 제공은
  gzip을 선택 사항으로 본다. 둘의 기준을 맞춘다.

## 3단계 — 성능과 중복 정리

### 3-1. 메시 요청마다 파일 전체를 읽고 해시를 다시 계산한다

- `core/mantle.py`, `core/collision.py`의 제공 함수가 요청마다 파일(메시 약 2.9 MB,
  단면 1.5 MB)을 메모리로 읽고 SHA-256을 계산한다. `catalogue.json`도 매번 다시 읽고,
  홈은 `annotations/mantle-overlay.json`을 렌더링마다 읽는다.
- 기존 엔드포인트는 `FileResponse`로 스트리밍하고, 해시 검증은 컨테이너 시작 시
  `verify_bundle.py`에 맡긴다. 같은 방식으로 바꾸거나, 파일 크기·수정 시각을 키로 검증
  결과를 프로세스 안에 캐시한다. `If-None-Match`에 304를 응답한다.
- 해시 URL이 바뀌지 않은 파일이 변조되면 404를 주던 성질이 필요한지 판단해 문서에 남긴다.

### 3-2. 파일 제공 코드 중복

- `collision.py`가 `mantle.py`의 카탈로그 읽기와 gzip·해시·ETag·Cache-Control 코드를
  복사했다. 이미 달라져서 collision 응답에는 `X-Content-Type-Options: nosniff`가 없다.
- 공용 함수 하나로 합치고, 1-1의 예외 처리와 3-1의 캐시도 그 한 곳에 둔다.

### 3-3. `accepts_gzip` 파싱

- `core/mantle.py:34-46`은 `encoding`을 `strip()`하지 않아 `"gzip ; q=1"`이 `"gzip "`
  키가 되어 압축되지 않은 응답을 보낸다. 대역폭만 손해이므로 3-2와 함께 고친다.

## 4단계 — 작은 UI·스크립트·문서 수정

- **같은 원본 시점 안의 재로딩:** `mantle-overlay.js:142`는 `age === frame.age_ma`까지
  요구한다. 40 Ma에서 타임라인을 35 Ma로 끌면 같은 40 Ma 시점인데도 메시를 숨기고
  다시 불러와 깜빡인다. 가까운 시점이 같으면 재로딩하지 않는다.
- **단면 팝업 오류 상태:** `collision.js`의 `setWaiting(true, error)`가 슬라이더를 잠근다.
  오류 후에도 다른 연대를 고르거나 팝업 안에서 재시도할 수 있게 한다.
- **대화상자 iframe 해제:** `collision-dialog.js:15`는 닫을 때 `src` 속성만 지운다.
  Chromium에서는 문서가 내려가지 않아 WebGL 컨텍스트와 ResizeObserver가 남을 수 있다.
  `about:blank`로 바꾸고, 브라우저 검사에서 속성뿐 아니라 문서 해제를 확인한다.
- **WebGL 컨텍스트 복구:** `mantle.js:134`는 `webglcontextlost`에서 `preventDefault()`만
  하고 `webglcontextrestored` 처리가 없다. 복구하거나 새로고침 안내를 표시한다.
- **대화상자 로딩 범위:** `templates/base.html`이 소개·개인정보·연락 페이지에도 단면
  대화상자 CSS·JS를 넣는다. 뷰어 페이지에서만 넣는다.
- **쓰이지 않는 문자열:** `core/mantle.py`의 중첩 `"unavailable"` 문구는 시간 범위가 켜지면
  `globe()`가 `None`을 반환해 보내지지 않는다. 제거하거나 실제로 쓴다.
- **라이선스 표기:** `LICENSE-DATA.md:16-17`에 인도–아시아 단면 묶음(OPT1 단면선·크라톤·
  경계와 PaleoDEM 유래 지형)을 추가한다. `templates/core/collision.html:49-51`에 CC BY 4.0
  링크와 변경 사항 표기를 `mantle.html`처럼 넣는다.
- **zip 내부 경로:** `scripts/build_india_asia.py:144,147`의 `Path`를 `PurePosixPath`로
  바꾼다(`build_mantle.py:135`와 동일). Windows에서 `KeyError`를 막는다.
- **PaleoDEM 입력 검증:** `build_india_asia.py:28-31`은 PNG 해시를 기록만 하고 PaleoDEM
  카탈로그와 비교하지 않는다. 불일치 시 중단한다.

## 5단계 — 유지보수 (선택)

- `static/core/mantle-overlay.js`는 한 줄에 여러 문장을 쓰는 압축 형태(100–145행 등)로
  주석이 많은 `globe.js`와 스타일이 다르고 diff 리뷰가 어렵다. 동작 변경 없이 풀어 쓴다.
- `globe.js`와 중첩 모듈이 서로를 호출한다(`selectStop`, `neighbourStop`, `setPlaying`,
  `setProjection`, 렌더 루프 ↔ `play`·`inspector`·`info-toggle` DOM id와 uniform 직접 접근).
  `globe.js:1794-1807`은 지표 실패를 상태 클래스와 `aria-busy`로 판정한다. 성공·실패를
  Promise나 콜백 값으로 넘기도록 바꾼다.
- 병합된 로컬 브랜치 7개와 원격 feature·docs 브랜치를 정리한다.

## 진행 방식

- 1–2단계는 `fix/…` 브랜치에서 PR로 올린다. 1-2는 화면 확인 결과에 따라 범위를 정한다.
- 3–4단계는 묶어서 별도 PR로 올릴 수 있다. 5단계는 동작 변경이 없음을 기존 브라우저
  검사(`tests/mantle-overlay-browser.mjs`, `tests/globe-browser.mjs`)로 확인한다.
- 버전 올림과 배포는 수정 병합 후 요청이 있을 때 별도로 진행한다. 런타임 자료 재생성은
  필요 없다(4단계 스크립트 수정은 이후 재생성 때 반영).
