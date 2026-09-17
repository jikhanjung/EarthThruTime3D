# v0.18.0 — 지구 내부 공통 절개 릴리스

## 변경

- PR #64를 병합해 CRUST 2.0과 맨틀 중첩을 지구 내부 패널에 모았다.
- 위도·경도 범위를 공유하며 날짜 변경선 횡단과 인도–아시아 프리셋을 지원한다.
- 절개 기본값 Off, 지표 불투명도 70%를 유지한다. 맨틀 활성화 시 현재 연대와 시점을 보존한다.
- 지각은 현재(0 Ma) 자료이며 맨틀과의 중첩은 서로 다른 모델의 근사 시각화다.
- 과학 자료 재생성·DB 스키마 변경 없이 정적 모듈 캐시 버전을 0.18.0으로 올린다.

## 배포 전 검증

[095](20260917_jikhanjung_095_shared_interior_cutaway.md)에 구현과 검증을 기록했다.
Django 83개 테스트, JavaScript 8개 테스트 파일, Chromium 지각·맨틀·연대 전환,
Firefox 지각·하천 회귀 검사가 통과했다.

## 운영 배포

- PR #64 구현, PR #65 버전 준비를 병합했다. 빌드 기준은 깨끗한 main `24e71ec`.
- 개발 호스트에서 build.sh 실행, Django 83개 및 이미지 smoke 통과 후 Docker Hub에 push했다.
- 이미지 digest: `sha256:35c09696edba41420bf552d4af428cb441edc315542ac7eb2eb21ac49538f1fc`.
- dolfinid-2에서 digest를 고정해 pull, 자료·호스트 묶음 SHA-256 확인 후 기존 deploy.sh로 교체했다.
- 자료 1,080개(445,775,830 bytes)의 경로·크기·해시가 v0.17.0과 모두 같다.
- 배포 직전 DB 백업: `db-20260917T063148Z.sqlite3` (131,072 bytes), 무결성 검사 통과.
- 운영 secrets 변경 없음. 호스트에서 실행 중 DB 쓰기·교체 없음.
- 공개 HTTPS health: 0.18.0 / ok, DB·스키마 정상, 기본 자료 90개 중 누락 0.
- HTML의 공통 절개 UI 및 새 모듈의 `?v=0.18.0` 캐시 키 확인.
- 공개 Chromium: 지각 자료 지연 로딩·재시도·캐시, 연대 제한, 평면 투영, 극·날짜 변경선·전체 경도 절개, 맨틀 공유와 모바일 검사 통과. 지각·맨틀 동시 표시 스크린샷 확인.
- 공개 Chromium Younger/Older: 로딩 중 지구 렌더링이 동일하게 유지되고 준비 후 지표·맨틀이 함께 교체됨을 확인.
- 공개 Firefox 146.0.1: 지각 색·절개·5배·20→0 Ma, 하천·빙하·네트워크·콘솔 검사 통과.
- 롤백: `bash /srv/earththrutime3d/deploy.sh v0.17.0` (DB 유지).

### 릴리스 묶음 SHA-256

```text
324b3ed123f7d323322325c3c835f8c0f8266eef1d854ba92f7cc71e143e9f5f  earththrutime3d-image-v0.18.0.tar.gz
ab70b9d1aa9e83b69edf37fa42bc935774cbfe5d6bfe435768d312212b0e7151  earththrutime3d-data-v0.18.0.tar.gz
c459ab2d2c8759e87c33aa61e1c81f53ce62b941706dcdb9c0c94118828e5563  earththrutime3d-host-v0.18.0.tar.gz
```
