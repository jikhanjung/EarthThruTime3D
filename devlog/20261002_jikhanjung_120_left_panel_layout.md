# jikhanjung 120 — 화면 배치: 왼쪽 세로 패널, 위쪽 띠 없앰, 범례는 오른쪽 아래

날짜: 2026-10-02 · PR: #118 · 참고: GSM 온 지구(`web/viewer/templates/viewer/earth.html`, `map.css` 의 `#panel`·`.box-head`·`.legend-dock`)

사람이 말했다: "범례 성격의 패널들을 우하단으로. Copyright 과 About 은 그 둘만 남겨서 하단 중앙으로. 컨트롤 패널은 ../GSM
을 참조해서 왼쪽에 세로로 긴 패널로. 상단 제목 줄은 띠 모양으로 하지 말고 왼쪽 제목은 왼쪽 세로 패널 제일 위로, 오른쪽
언어 설정은 floating 으로 … 모바일에서는 햄버거 버튼으로 왼쪽 패널을 불러내게 하고 … 범례도 사용자가 원하면 접을 수
있게." 이어서 "타임라인 슬라이더는 하단에 남겨도 될 것 같아. 그건 가로로 길쭉한 게 좋을 테니까."

## 바꾼 것

- **왼쪽 패널**(`#side-panel`, 300 px): 맨 위 제목·판(`.side-brand`), 그 아래 GSM 의 상자 꼴(머리에 왼쪽 청록 띠)로 "보기"
  (표시 자료·투영·시점 초기화 — 예전 아래 조작판의 툴바)와 "레이어"(예전 ☰ 팝업 메뉴 `#settings-menu`, 이제 늘 보임).
- **☰(`#settings-toggle`)** 은 패널을 접고 편다. 넓은 화면에서는 처음에 펴져 있고, 지구본·정보·타임라인·범례를 담은
  `.stage-area` 가 패널 옆 나머지 폭을 쓴다 — 무대 크기가 바뀌면 기존 ResizeObserver 가 카메라를 다시 맞춘다. 접은 상태는
  이 브라우저가 기억한다(`earththrutime.side`). 버튼 id 를 그대로 두어 다른 시험들이 그대로 쓴다.
- **폭 899 px 이하**: 패널은 처음에 접힌 서랍(`position:fixed`, `min(320px, 86vw)`)이다. ☰이 지도 위로 밀어 내고, 지도를
  누르거나 Escape 로 닫힌다. 언어 줄은 서랍 아래로 간다.
- **위쪽 띠 없앰**: 지구본 쪽에서 `header` 는 언어(KO | EN)만 오른쪽 위에 떠 있고, 정보 버튼은 그 아래(48 px), 정보 패널은
  90 px 부터.
- **범례**: 기온·식생·강수·바람·해류 범례를 한 상자(`#map-legend`)에 모아 오른쪽 아래, 타임라인 위에 둔다. 머리 "범례"를
  누르면 접힌다(`earththrutime.legend`). 정보 패널은 그 위에서 멈춘다(`--legend-space`, ResizeObserver). 휴대폰에서는
  타임라인 위 전체 폭. 해류 범례 칸은 좁은 상자에서 잘리지 않게 `auto-fill` 로.
- **타임라인**: 아래에 가로로 긴 판 그대로(툴바만 빠졌다).
- **바닥글**: 지구본 쪽에서는 © PaleoBytes · 소개만 아래 가운데. 개인정보·문의는 `footer-more` 로 숨기고 소개 쪽 "문의"
  줄에 개인정보 링크를 더했다. 다른 쪽(소개·개인정보·맨틀)은 예전 바닥글 그대로다.

## 시험

- `tests/globe-browser.mjs` 를 새 배치에 맞췄다: 넓은 화면에서 패널이 보이고 지구본이 그 오른쪽에서 시작, 머리 줄의 제목
  없음·언어 보임·바닥글의 개인정보 숨김, ☰ 로 접으면 지구본이 왼쪽 끝부터, 다시 펴기. 휴대폰: 패널이 숨은 채로 시작, ☰ →
  서랍(폭 351 px 이하), 지도를 누르면 닫힘, 가로로 눕힌 짧은 화면에서도 서랍이 화면 안. 예전 "툴바 한 줄"·"메뉴가 조작판
  안"·"해수면 곡선이 메뉴 위" 검사는 없앴다.
- river·view-address 는 ☰ 을 무조건 누르던 것을 "메뉴가 숨어 있을 때만" 으로.
- 통과: flux(현재 지구 자료 있는 서버), view-address·river·pin·climate·crust·interior-navigation·mantle-overlay·collision·mantle·
  globe(자료 없는 서버). npm 49, Django 98. 스크린숏 `data/screenshots/ui-{desktop,desktop-present,phone,phone-drawer}.png`.
