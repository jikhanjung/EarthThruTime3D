# dolfinid 의 "Dead" 무작위 이름 컨테이너 — 매시 백업의 일회용 컨테이너

상태: 2026-11-14 원인 확인, 저장소 스크립트 수정. 서버의 `backup.sh`·`deploy.sh` 는 아직 앞 판이다.

## 관측

- banjang 점검(`ops/collect.py`, m710q 에서 10분마다 dolfinid 로 `docker ps -a`)이
  `honestjung/earththrutime3d:v0.26.1` 의 무작위 이름 컨테이너를 Dead 로 두 번 잡았다:
  11-13 08:00:31 KST `nervous_shirley`, 17:00:28 KST `flamboyant_wilson`. 11-14 에 사용자가 다시
  봤을 때는 Dead·Exited 가 없었다.
- dolfinid dockerd journal: `nervous_shirley` 2026-11-12 23:00:28.10Z 에 네트워크 연결, 28.57Z 에
  task 삭제. `flamboyant_wilson` 11-13 08:00:25.03Z → 25.62Z. 두 시각에
  `earththrutime3d-backup.service` 가 돌았고 둘 다 "Backed up to db-…sqlite3", "Kept the newest 24"
  로 정상 끝났다.
- banjang-wake 의 수집 시각(08:00:25–31, 17:00:22–28 KST)이 두 컨테이너가 살던 시각과 초 단위로 겹친다.
- 같은 꼴의 무작위 이름(`hopeful_wing`, `stoic_hopper`, `elegant_ellis` …)이 매시간 하나씩 생겼다 지워진다.

## 해석

`backup.sh` 는 sqlite 스냅샷을 일회용 컨테이너(`docker run --rm`, 이름 없음)에서 뜬다. docker 는 `--rm`
정리 중 파일 시스템을 지우기 전에 컨테이너를 dead 로 표시하므로, 그 순간의 `docker ps -a` 에는 Dead 로
보인다. 백업 타이머는 정시 + 0–300초, banjang 은 10분마다 + 0–30초라서, 백업이 정시 30초 안에 떨어진
시간에만 겹친다. 고장이 아니고 남은 컨테이너도 없다.

다른 후보: `deploy.sh` 의 묶음 검증(`docker run --rm`)은 배포 때만 돌고 11-13 에는 배포가 없었다.
`smoke_image.py` 는 빌드 호스트에서 돈다. m710q 의 `backup-earththrutime.sh`(04:20)는 ssh·scp 만 쓴다.
`docker-prune-keep` 은 이미지만, healthcheck 는 `exec` 라 컨테이너를 만들지 않는다.

## 바꾼 것

- `deploy/host/backup.sh`: 일회용 컨테이너에 `--name earththrutime3d-backup-<UTC 시각>-<PID>`,
  `--label earththrutime3d.role=backup`. 고정 이름은 배포의 백업과 타이머가 겹칠 때 충돌하므로 시각과
  PID 를 붙였다.
- `deploy/host/deploy.sh`: 묶음 검증 컨테이너에 `earththrutime3d-verify-<버전>-<PID>`,
  `earththrutime3d.role=verify`.
- `deploy/README.md` 백업 절에 이름·표지와 Dead 로 잠깐 보이는 까닭을 적었다.

## 남은 일

- 서버 반영: 호스트 스크립트는 저장소에서 따로 복사한다(2026-10-07 `backup.sh` 교체와 같은 방식). 다음
  배포 때나 따로 지시가 있을 때 바꾼다. 그때까지 서버의 컨테이너는 계속 무작위 이름이다.
- banjang 쪽: Dead 를 다음 수집에도 남아 있을 때만 알리거나, `earththrutime3d.role` 표지가 있으면 거르는
  것은 banjang 저장소의 일이다(banjang 에 알림).
