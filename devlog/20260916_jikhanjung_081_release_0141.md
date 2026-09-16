# v0.14.1 — 맨틀 표시 기본값 배포

상태: 2026-09-16 운영 배포·공개 브라우저 검증 완료.

- #49 병합 `9656095`: 절개 Off, Surface opacity 70%.
- 원본·파생 자료는 v0.14.0과 동일하며 앱·Docker·배포 버전을 0.14.1로 맞춘다.
- 배포 전 v0.14.0 healthy, 디스크 여유 16 GB. 운영 DB와 비밀 설정을 보존한다.
- #47 Firefox 검사와 #48 호수 표시는 별도 검토 중이며 이 릴리스에 포함하지 않는다.

## 결과

- 릴리스 설정 #51 병합 `04821c9`; 이미지 소스는 그 안의 깨끗한 커밋 `b38e924`.
- `make check`, `make test` 77개, 이미지 빌드 검사 및 컨테이너 스모크 통과.
- 1,077개 파일, 430,456,637 bytes. v0.14.0과 모든 파일 경로·SHA-256 일치.
- 이미지 `sha256:0796042806b884c6ce4598e105e03ca8ae7375ef200bc4de4e7bf1f14adac85a`.
- 전송 후 아카이브 3개 해시 및 운영 자료 1,077개 검증 통과.
- DB 스냅샷 `db-20260916T032018Z.sqlite3`, 131,072 bytes, 검증 완료.
  `.env.django` 배포 전후 해시 일치. 운영 DB 유지.
- 운영 컨테이너 healthy, 상태 응답 `ok`, `0.14.1`, DB·스키마 정상, PaleoAtlas 90개·누락 0.
- 공개 Firefox에서 절개 체크 해제, 슬라이더 70과 표시 70%, 실제 렌더 상태
  `data-mantle-cutaway=false`, `data-mantle-opacity=0.7` 확인.
  오버레이를 끄면 지표 불투명도가 1로 돌아오며 페이지 오류가 없었다.
- 롤백: `bash /srv/earththrutime3d/deploy.sh v0.14.0` (DB 유지).

| 아카이브 | SHA-256 |
|---|---|
| image-v0.14.1.tar.gz | `268e666b5bc8f9eb666e8d10dd3cf2d8f50767af57462d8c5fbc1cebb8d7a6b8` |
| data-v0.14.1.tar.gz | `2dbec0ab356d79f20d28a6b20c25c0de5cb31fa918e2a36ea9431c84d0c2b670` |
| host-v0.14.1.tar.gz | `c459ab2d2c8759e87c33aa61e1c81f53ce62b941706dcdb9c0c94118828e5563` |
