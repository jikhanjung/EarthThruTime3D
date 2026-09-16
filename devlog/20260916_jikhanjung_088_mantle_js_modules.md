# 맨틀 JS 정리와 화면·렌더링 모듈 분리

날짜: 2026-09-16 · 브랜치: `refactor/mantle-modules` · 기준 main `c248f34`

## 범위와 구조

P06 배포 후 재검토에 이어 사용자가 JS 정리·모듈 분리, PR 병합 및 배포를 요청했다.
기존 브랜치는 모두 유지한다. 데이터 생성·좌표계·연대 간격·과학 모형은 변경하지 않는다.

- `mantle-overlay.js`의 압축된 다중 문장을 풀고 로딩·연대 선택·오류/재시도·UI를 읽기 쉽게 정리했다.
- `mantle-scene.js`로 Three.js 변환, 메시 디코딩·생성, 조명·핵·단면선,
  GPU 자원 해제, 절개·불투명도, 단면선 선택 판정을 분리했다.
- `globe.js`의 `mantleBridge`가 공유 타임라인·카메라·투영·재생·정보 패널을 담당한다.
  중첩 제어 모듈은 공유 DOM id나 surface uniform에 직접 접근하지 않는다.
- scene은 `prepare`의 결과로 `commit`/`dispose`를 제공한다. 새 메시 준비는 기존 화면을
  바꾸지 않으며, 지표와 맨틀이 모두 준비되면 같은 프레임에 교체한다. 취소 결과는 해제한다.
- 기존 수치 검사를 새 모듈 경계로 옮기고, 바이트 길이·잘못된 인덱스·NaN 좌표를
  GPU 생성 전에 거부하는 검사를 추가했다.
- Prettier 3.6.2를 일회성으로 사용했다. 프로젝트 의존성이나 빌드 도구는 추가하지 않았다.
  행렬은 행/열 구조를 읽을 수 있도록 유지했다.
- 기능 동작을 유지하는 릴리스로 앱·Docker·배포 버전을 0.15.1로 맞춘다.

## 검증

- 변경 전 Chromium의 Younger/Older 지구 유지 검사 통과.
- 변경 후 `make check`, `make test` Django 77개, `npm test` 6개 파일 통과.
- 변경 후 Younger/Older 양방향의 로딩 중 픽셀 유지와 준비 후 형상 교체 통과.
- Chromium 중첩 검사 통과: 다섯 연대·절개/투명도·팝업 동기화·오류 재시도·문서 해제·취소·모바일·영문.
- Chromium 전체 지구본 17개 구간 통과: 기존 지도·PaleoAtlas·PaleoDEM·판/해안선·시간 창·조작·오류 복구.
- Firefox 146.0.1 + Xvfb: 새 모듈 로딩, Off/70% 기본값, 실제 렌더 상태, Younger/Older 80→60→80,
  중첩 해제 시 불투명도 1 복원과 페이지 오류 없음 확인.
- 버전 반영 후 make check·Django 77개·JS 6개 파일 및 git diff --check 재확인 통과.

배포 결과는 [089](20260916_jikhanjung_089_release_0151.md)에 기록한다.

## 배포 전 캐시 호환성 보완

#55 병합 후 이미지 생성 단계에서 기존 WhiteNoise의 1시간 캐시 정책을 다시 확인했다.
엔트리 `globe.js`만 버전이 바뀌고 중첩 모듈은 같은 URL이면, 방문자 캐시에 남은 옛 API와
새 호출부가 섞일 수 있다. 첫 준비 이미지는 배포하지 않았다.
홈 import map의 `mantle-overlay.js`·`mantle-scene.js`에 릴리스 버전을 붙이고,
두 모듈이 같은 앱 버전으로 매핑되는지 회귀 검사를 추가했다. 기존 브랜치는 유지한다.
`make check`, Django 78개, JS 6개 파일, 최종 import map을 사용하는 Firefox의 기본값·
Younger/Older·해제 복원 검사가 통과했다.
