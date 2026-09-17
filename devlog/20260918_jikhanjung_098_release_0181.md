# v0.18.1 — 절개 뒷면·지구본 조작 수정 릴리스

## 변경

PR #67의 절개 뒷면 표시, 투명 지각 렌더링 순서 및 모든 지구본의 pan·zoom·tilt
통일을 배포한다. [097](20260917_jikhanjung_097_interior_navigation_backfaces.md)에
원인·구현·회귀 검증을 기록했다. 과학 자료와 DB 스키마는 바꾸지 않는다.
정적 파일 캐시 키를 0.18.1로 올려 기존 브라우저에도 수정된 모듈을 제공한다.

## 검증과 운영 배포

- PR #67 구현과 PR #68 릴리스를 병합했다. 깨끗한 main `6cfb840`에서 빌드했다.
- `make check`: 번역 400개, 설정·마이그레이션 검사 통과.
- `make test`: Django 83개, `npm test`: JavaScript 8개 파일 통과.
- 개발 호스트의 build.sh 및 이미지 smoke 통과 후 Docker Hub에 push했다.
- 이미지 digest: `sha256:3c653a2c354c58a648ce647f86b0a1b1ff2d143a1f5af76163663288913cfc45`.
- dolfinid-2에서 digest를 고정해 pull하고 자료·호스트 묶음 SHA-256을 검증했다.
- 자료 1,080개(445,775,830 bytes)의 경로·크기·해시가 v0.18.0과 모두 같다.
- 배포 직전 DB 백업: `db-20260917T152004Z.sqlite3` (131,072 bytes), 무결성 검사 통과.
  파일명은 UTC, 배포일은 한국 시각 2026-09-18이다.
- 기존 deploy.sh로 교체했다. 운영 secrets 변경 없음, 실행 중 DB를 호스트에서 쓰거나 교체하지 않음.
- 공개 HTTPS health: 0.18.1 / ok, DB·스키마 정상, 기본 PaleoAtlas 90개 중 누락 0.
- 공개 HTML의 `globe.js?v=0.18.1`, `crust.js?v=0.18.1` 및 pan·tilt 안내 확인.
- 공개 Chromium: PaleoAtlas·PaleoDEM 각각 절개 뒷면, pan·zoom·tilt, Shift 입력 분리,
  reset·투영 전환의 모든 assertion 통과. 절개 안쪽 스크린샷도 확인했다.
- 공개 100%→99% 불투명도 비교: 두 자료 모두 RGB 평균 변화 0.18/255 (기준 5 미만).
- 전체 브라우저 실행은 모든 assertion 로그 후 종료 단계에서 exit 143으로 중단되어,
  동일 검사에서 고도 지구본만 별도 실행했다. 모든 assertion과 정상 종료(exit 0)를 확인했다.
- 공개 Firefox 146.0.1: 지각·절개·5배·20→0 Ma, 하천·빙하·콘솔·네트워크 검사 통과.
- 롤백: `bash /srv/earththrutime3d/deploy.sh v0.18.0` (DB 유지).

### 릴리스 묶음 SHA-256

```text
b59fd445bca5f3495cb47963e727f17cacc47c71353bc0f24a7b175ab6086193  earththrutime3d-image-v0.18.1.tar.gz
50908d4d2b4795c87bf1d9eba68a2a3130e72e2f243fca48977a41722fe8a128  earththrutime3d-data-v0.18.1.tar.gz
c459ab2d2c8759e87c33aa61e1c81f53ce62b941706dcdb9c0c94118828e5563  earththrutime3d-host-v0.18.1.tar.gz
```
