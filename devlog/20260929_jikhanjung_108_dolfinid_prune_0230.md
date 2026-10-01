# dolfinid 배포 파일 정리 (v0.23.0 이후)

날짜: 2026-09-29

사용자 요청으로 dolfinid의 EarthThruTime3D 디스크 사용을 점검하고 배포 파일을 정리했다.
절차는 [099](20260918_jikhanjung_099_dolfinid_release_cleanup.md),
[104](20260920_jikhanjung_104_dolfinid_prune_0200.md)와 같다.

## 점검

- 실행 전: v0.23.0 healthy, `/` 77G 중 52G 사용 / 여유 26G (68%).
- 이 프로젝트가 쓰는 공간은 약 5.0 GB였다. 104 이후 v0.19.0–v0.22.0이 다시 쌓였다.

| 위치 | 크기 | 내용 |
|---|---|---|
| `/srv/earththrutime3d/data/` | 2.3G | v0.19.0 (452M), v0.20.0·v0.21.0·v0.22.0 (각 463M), v0.23.0 (464M) |
| `~/earththrutime3d-release/` | 1.9G | v0.19.0–v0.23.0 릴리스 묶음, data tar.gz 버전당 약 380 MB |
| Docker 이미지 | 약 0.8G | 5개 태그. 공유 레이어 177 MB에 버전당 약 75 MB, v0.19.0만 공유 없이 263 MB |
| `backups/` | 1.8M | 매시간 스냅샷 14개(보관 개수대로) |
| `db/` | 260K | |

- 서버의 `prune.sh` 해시가 저장소 `deploy/host/prune.sh`와 같음(`446663ec…`).
  `DRY_RUN=1`(기본 `KEEP=2`)로 대상 확인.

## 정리

- `bash prune.sh`: **v0.21.0, v0.20.0, v0.19.0** 삭제 — 이미지 3개, `data/<version>` 3개,
  릴리스 tar.gz·SHA256SUMS. **+2,877 MiB** 확보. v0.23.0(운영)과 v0.22.0(롤백)은 유지.
- 실행 후: 49G 사용 / 여유 28 GiB (64%). 남은 것은 `data/` 927 MB, 릴리스 묶음 744 MB,
  이미지 2개.
- `/healthz` 200, `smoke.sh` 통과(0.23.0, 90 land fields), 컨테이너 재시작 없음.
  DB·백업·secrets·운영 스크립트와 다른 프로젝트는 건드리지 않았다.
- `docker system df`의 회수 가능 3.4 GB는 대부분 이 호스트의 다른 서비스 이미지라
  사용자 판단에 맡긴다.
