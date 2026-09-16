# 맨틀 근사 중첩 기본값 변경

사용자 요청에 따라 Approximate mantle overlay의 초기 표시를 변경했다.

- India–Asia surface cutaway: Off.
- Surface opacity: 70%. 슬라이더와 퍼센트 표시를 함께 변경했다.
- 기존 연대 전환 브라우저 검사의 절개 조작은 현재 상태를 뒤집는 방식 대신
  명시적인 `uncheck()`로 바꿨다.
- `make check`, `make test`(77개), 렌더된 HTML의 체크 상태·슬라이더 값·표시값 확인 통과.
- 이번 변경의 운영 배포는 아직 수행하지 않았다.
