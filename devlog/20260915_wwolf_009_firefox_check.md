# wwolf 009 — Firefox 검사를 저장소에: WebDriver BiDi로 데스크톱 Firefox 구동

날짜: 2026-09-15 · 브랜치: feature/firefox-check (main 위, v0.14.0 뒤) · 관련: #38, #39 검토(jikhanjung 073), #44

## 배경

#38의 import map 버그는 Chrome이 관대해서 Chromium 검사로는 잡히지 않았고, Firefox에서만
지구본이 영원히 "준비 중"이었다. 소유자는 #39 검토에서 Firefox 146을 Xvfb와 소프트웨어
렌더링으로 손수 띄워 확인했다(073). 이 Mac에서는 Playwright의 Firefox 빌드가 깨져 있어
(libmozglue.dylib 없음), 지난 두 세션은 임시 스크립트로 데스크톱 Firefox를 WebDriver BiDi로
구동해 확인했다. 그 스크립트를 저장소의 검사로 옮긴다.

## 구현: `tests/firefox-browser.mjs`

- Playwright 없이 Node의 WebSocket으로 BiDi 세션을 연다. `FIREFOX_BIN`(기본 macOS 앱 경로,
  Linux에서는 `firefox`)을 `--headless --no-remote --profile <임시> --remote-debugging-port`로
  띄우고, `session.new` → `session.subscribe`(log, network) → `browsingContext.navigate` →
  `script.evaluate` → `browsingContext.captureScreenshot`. headless라 Xvfb가 필요 없다.
- 고정 대기 대신 `#globe`의 data 속성을 0.5초마다 읽어 조건이 될 때까지 기다린다(상한 30초).
  검사: `data-frame`이 정해지고 `aria-busy`가 false, `data-rivers` true; 해수면 −60 m에서
  시점 목록이 있으면 `data-river-ice`가 비지 않음(없으면 `data-river-low` > 0); 2.5만 년 창
  20 ka에서 `data-ice-age` 20, 시점이 있으면 `data-river-ice` 20.0; 콘솔 error 0, HTTP ≥ 400과
  fetch 실패 0(페이지가 이동하며 스스로 끊은 NS_BINDING_ABORTED는 제외). 스크린샷은
  `test-results/firefox-lowstand.png`, `firefox-deglacial-20ka.png`.
- 끝나면 자기가 띄운 Firefox 프로세스만 죽이고 임시 프로필을 지운다. 지난 세션에서
  `pkill plugin-container`가 열려 있던 Firefox 창까지 죽인 일이 있어 PID로만 다룬다.

## 확인

- Firefox 155.0.1, 개발 서버(:8000, feature/ice-rivers + fetch 수정): 7초에 통과.
  −60 m에서 `data-river-ice` 12.7, 창 20 ka에서 20.0·`data-ice-age` 20, 오류 0.
- docs/globe-viewer.md "Verification"에 항목을 더했다.

## 남은 일

- Linux 헤드리스 Firefox의 WebGL은 확인하지 않았다(소유자의 Xvfb 환경). 실패하면
  `MOZ_HEADLESS`와 소프트웨어 렌더링 설정을 프로필에 넣는 것이 다음 단계다.
