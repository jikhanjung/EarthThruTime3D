# issue #50 — 변하는 Zenodo 메타데이터와 고정 원본 분리

- OPT1 manifest의 필수 assets에서 API record.json을 제거했다. ZIP의 크기·SHA-256은 유지했다.
- 라이선스 근거에 API URL, 2026-09-16 조회일, 확인한 license/version을 기록했다.
  JSON은 선택적인 근거 자료이며 빌드 입력이 아니다. 공용 검증 함수는 완화하지 않았다.
- 오프라인 회귀 검사: record 없음/조회수 변경은 허용하고 손상된 ZIP은 거부한다.
- `make check`, Django 77개, geodynamics 검사 6개 통과.
- 실제 고정 ZIP verify-only 통과. `/tmp`에 맨틀 0 Ma와 인도–아시아 5시점을 재생성했다.
  단면 결과 1,510,100 bytes, gzip 420,502 bytes. 기존 파생 자료를 덮어쓰지 않았다.
