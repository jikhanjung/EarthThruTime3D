# jikhanjung 064 — 시간 범위: 최근 13만 년

날짜: 2026-09-15 · 브랜치: feature/last-glacial-cycle · 계획: [jikhanjung P02](20260915_jikhanjung_P02_last_glacial_cycle.md)

## 한 것

- "시간 범위"에 "최근 13만 년"(`?window=lastcycle`)을 더했다. 130 ka부터 현재까지 1천 년 간격 131개
  시점이고, "최근 2.5만 년"은 그대로 둔다.
- 서버(`core/globe.py`):
  - `deglacial_frames` 를 `window_frames(frames, kinds, stack, reach)` 로 일반화했다.
    `WINDOWS` 는 범위별 나이 표다(25, 130).
  - 조각이 있는 나이는 발표된 복원 조각을 쓴다(`ice_kind` `dated`). 해수면은 조각의 이어 받은 값이다.
  - 조각이 없는 나이(26–130 ka)는 가정 빙하다(`analogue`). 현재 프레임의 `ice_sheet`·`ice_lows` 를 남기고,
    해수면은 스택 값을 그대로 쓴다(`deglacial.url` 없음).
  - 창의 모든 프레임은 기온이 없다.
- 페이지:
  - 조각을 바로 쓰는 경로는 `deglacial.url` 이 있을 때만 탄다. 가정 빙하 프레임은 기존 해수면 가정 경로를
    그 해수면으로 탄다. 그 해수면에서 후퇴기 조각 둘을 섞는다.
  - `data-ice-kind` `analogue`, 캡션 "가정 빙하", 안내문(`#ice-analogue-note`). 안내문은 성장기와 후퇴기의
    모양 차이를 무시한다는 것, 스택이 마지막 간빙기 +6~9 m 를 재현하지 않는다는 것을 알린다.
  - 범위에 따라 해수면 색띠 제목을 바꾸고, 범례와 시점 수 문구를 범위와 무관하게 고쳤다. 영어 번역 5개를
    더하고 2개를 바꿨다.
- 0 Ma 고도 텍스처 12비트:
  - `build_paleodem.py` 는 `--bits` 와 상관없이 현재 격자를 12비트로 쓴다.
  - `paleodem-0000` 만 다시 만들었다. 2048×1024, 파란 채널 최대 15, 1.67 MB → 2.82 MB.
  - 나머지 108장은 8비트 그대로다.
- 문서: `docs/globe-viewer.md` "Time window" 에 최근 13만 년.

## 계획에서 달라진 것

- 0 ka 프레임은 현재의 `ice_kind`(natural-earth)를 그대로 둔다. 조각 경로도 가정 경로도 아니고,
  해수면 0 에서 현재 빙하를 보인다.
- 21 ka 의 `data-ice-kind` 는 `dated` 가 아니라 기존 값인 `drawn` 이다. 페이지는 한계선(limit)과
  가정(analogue)만 따로 구분한다.

## 확인

- `make check`, `make test` 53개(최근 13만 년 검사 1개 추가), `npm test` 13개 통과.
- 브라우저 검사 전체 통과. 새 "Last glacial cycle" 항목의 내용:
  - 131개 시점, 슬라이더 최대 130.
  - 21 ka: `drawn`, 가정 안내문 숨김.
  - 70 ka: `analogue`, 안내문 보임, `data-ice-low` 채워짐, 해수면이 스택 값, 슬라이더 잠김.
  - 121 ka: 저수위 조각 없음.
- 정거원통 스크린숏 비교:
  - 21 ka 는 로렌타이드·코딜레라·스칸디나비아 빙상과 넓어진 대륙붕이 보인다.
  - 121 ka 는 해수면 +0 m 에 현재와 같은 빙하다.
  - 빙하의 대비는 크다. 해안선 변화는 전 지구를 한 화면에 보면 여전히 작고, 대륙붕이 넓은 곳을
    확대해야 잘 보인다.

## 남은 것

- 배포 전이다. 자료 묶음은 0 Ma 텍스처 약 1.2 MB 가 늘어난다. 빙하 자료는 그대로다.
- 개발 호스트 밖에서 빌드한다면 `build_paleodem.py --width 2048 paleodem-0000` 한 번이 필요하다.
- P02 의 "나중에": 간빙기 고수위 자료, 135–140 ka, 최근 80만 년, 성장기 모양, GIA.
