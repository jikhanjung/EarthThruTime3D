# dolfinid 배포 파일 정리 (v0.20.0 이후)

날짜: 2026-09-20

사용자 요청으로 dolfinid-2의 EarthThruTime3D 배포 파일을 정리했다. 절차는
[099](20260918_jikhanjung_099_dolfinid_release_cleanup.md)와 같다.

- 실행 전: v0.20.0 healthy, 디스크 47G 사용 / 여유 11G (82%). 서버의 `prune.sh` 해시가
  저장소 `deploy/host/prune.sh`와 같음(`446663ec…`). `DRY_RUN=1 KEEP=2`로 대상 확인.
- `KEEP=2 bash prune.sh`: **v0.18.1, v0.18.0** 삭제 — 이미지 2개, `data/<version>` 2개(856 MB),
  릴리스 tar.gz·SHA256SUMS. **+1,784 MiB** 확보. v0.20.0(운영)과 v0.19.0(롤백)은 유지.
- 실행 후: 45G 사용 / 여유 13G (79%). `smoke.sh 0.20.0` 통과, 컨테이너 재시작 없음.
  DB·백업(1.8 MB)·secrets·운영 스크립트는 건드리지 않았다.
- 이 프로젝트 밖의 큰 항목은 지우지 않고 사용자 판단에 맡긴다: 다른 프로젝트의 옛 Docker 이미지
  (`docker system df` 기준 회수 가능 2.5 GB, 미태그 2개 740 MB 포함), systemd 저널 1.2 GB,
  apt 캐시 131 MB, `~/projects` 8.7 GB, `~/hanyang3d-release` 1.7 GB, `~/venv` 1.5 GB.
