# EarthThruTime3D Docker 배포

이미지: **`honestjung/earththrutime3d:v0.14.1`**, 플랫폼 `linux/amd64`.
`../hanyang3d/deploy`의 Gunicorn·버전 이미지·Compose·상태 확인 구성을 참고했고,
데이터베이스가 있는 서비스이므로 백업과 복구 단계를 더했다.

2026-09-16 v0.14.1 운영 배포 완료. 이미지 ID:
`sha256:0796042806b884c6ce4598e105e03ca8ae7375ef200bc4de4e7bf1f14adac85a`.
배포·백업·공개 화면 검증 결과는 [릴리스 기록](../devlog/20260916_jikhanjung_081_release_0141.md)에 있다.

## 운영 주소

2026-09-12 dolfinid에 배포했다.

- 지구본: https://earththrutime.nopeoplestime.info/
- 인도–아시아 단면·3D 지표: https://earththrutime.nopeoplestime.info/collision/
- 맨틀 모형: https://earththrutime.nopeoplestime.info/mantle/
- 프로젝트 소개: https://earththrutime.nopeoplestime.info/about/
- 상태 확인: https://earththrutime.nopeoplestime.info/healthz

호스트 Nginx의 전용 사이트가 컨테이너의 8014 포트로 연결된다. HTTP는 HTTPS로 보낸다.
Let's Encrypt 인증서와 webroot 자동 갱신을 설정했고 갱신 후 `nginx -t && systemctl reload nginx`를
실행한다. 설정 원본은 [earththrutime3d.nginx.conf](host/earththrutime3d.nginx.conf)에 있다.

## 무엇을 배포하고 무엇을 배포하지 않는가

배포 자료는 2002년 웹 지도·2016년 PaleoAtlas에서 분할한 육지 거리장, PaleoDEM과
기온·해수면·빙하 파생 자료, PaleoCoastlines, 여러 판 모델이다. 자료별 조건은
[sources/README.md](../sources/README.md)와 [LICENSE-DATA.md](../LICENSE-DATA.md)를 따른다.
CC BY 자료의 파생물과 원본 조건이 확정되지 않은 마스크를 같은 라이선스로 취급하지 않는다.
비공개 판 모델은 접근 키 정책을 따르며, 자료 묶음에 존재하는 것과 공개 제공은 별개다.

원본 PALEOMAP 지도 이미지는 컨테이너·자료 묶음·운영 서버에 넣지 않는다. 웹 지도 이용
안내는 출처를 표시한 개인·교육·연구·학술출판 용도를 허용하면서 인터넷 게시를 저자 동의가
필요한 용도의 예로 든다. 기존 운영에서는 분할한 거리장을 출처와 함께 제공하며,
원본 제외가 파생 자료의 이용 조건까지 확정한다는 뜻은 아니다.

`SCOTESE_SOURCE_MAPS_PUBLIC=false`가 이 결정을 코드에서 강제한다. `/globe/maps/`는 404이고,
원본 미리보기와 원본 표면 전환 버튼은 렌더되지 않는다. 뷰어는 파생 마스크·고도 텍스처와
선택한 오버레이로 동작한다. `SCOTESE_VIEWER_ENABLED=true`와 원본 공개 여부는 별개다.
빌드 검사가 이미지 안에 JPEG가 없는지, 실행 중인 컨테이너가 원본을 내보내지 않는지
직접 확인한다.

## 구성

- 이미지: Django 코드, 템플릿, 정적 파일(빌드 시 collectstatic), 카탈로그, 이름 주석, 배포 도구.
- 데이터 묶음(`deploy/pack_data.py`):
  - 2002년 지도 17장의 거리장·조각 보고서와 2016년 PaleoAtlas 90장의 거리장·조각 보고서·이동 자료.
  - PaleoDEM 고도 텍스처 109장, 이동 자료, 기온 텍스처·곡선, 해수면 곡선, 빙하 마스크·출처,
    마지막 빙하기 후퇴 시기의 저수위 조각. 고도 시리즈는 생성 디렉터리가 있을 때 포함한다.
  - 잠재 하천 필드 109장과 저수위 필드 31장(2048×1024), 위도 경계 수정 후 전부 재생성.
  - PaleoMIST 1.0 빙하 하천 10장(2.5–25 ka, 2.5 ka 간격)과 시점 목록. 검증된 원본으로 생성.
  - PaleoCoastlines의 시기별 JSON과 인덱스.
  - 판 모델별 회전·대륙 JSON, 있는 모델에 한해 추가 해안선 JSON.
  - OPT1 맨틀 51시점과 인도–아시아 5시점 단면·3D 지표, 각 카탈로그 및 gzip 표현.
    실험 데이터는 누락·해시 불일치·시점 누락 시 패킹을 거부한다.
  경로·크기·SHA-256을 `manifest.json`에 기록한다. v0.14.1 릴리스에는 고도 시리즈와
  빙하 마스크 57장, 저수위 조각 25장, 12비트 0 Ma 고도 텍스처가 포함됐다. 정확한 파일 목록은 릴리스 묶음의 매니페스트를 따른다.
- 컨테이너: Gunicorn, UID/GID `10001`, 읽기 전용 루트, 쓰기 가능한 곳은 DB 볼륨과 `/tmp`뿐.
- 시작 순서: 설정 검사 → `migrate` → 묶음 해시 검증 → Gunicorn. 버전이 어긋난 묶음으로는 뜨지 않는다.
- `/healthz`: DB·스키마와 기본 자료 시리즈의 필수 필드 존재를 검사한다. 현재 기본값은
  `paleoatlas2016`이며 기대값은 90장이다. 필수 항목이 없으면 503, 검사가 통과해도
  `INTEGRITY_FAIL` 표식이 있으면 `degraded`/200이다. 모든 선택 레이어를 검사하는 것은 아니다.
  `smoke.sh`는 상태 `ok`, 버전 일치, 필수 필드 누락 0을 요구한다.

## 배포 동작

| 동작 | 명령 |
|---|---|
| preflight·build | `bash deploy/build.sh v0.14.1` (개발 호스트) |
| deploy | `bash /srv/earththrutime3d/deploy.sh v0.14.1` |
| backup | `bash /srv/earththrutime3d/backup.sh` |
| smoke | `bash /srv/earththrutime3d/smoke.sh` |
| rollback | `bash /srv/earththrutime3d/deploy.sh <이전 버전>` |
| prune | `bash /srv/earththrutime3d/prune.sh` (`KEEP`, `DRY_RUN=1`) |
| seed | 없음. 데이터베이스에 지질 기록이 아직 없다. |

`build.sh`는 Django 검사 → 마이그레이션 누락 확인 → 테스트 → 데이터 묶음 → 이미지 빌드 →
컨테이너 실행 검사 → 내보내기 순서다. 컨테이너 검사는 단면·3D 지표의 다섯 시점,
맨틀 현재 메시와 압축 응답도 확인한다. Docker Hub push나 원격 배포는 빌드에 포함하지 않는다.

`deploy.sh`는 이미지와 데이터 쌍을 먼저 검증하고, 데이터베이스를 스냅샷한 뒤 교체하고,
스모크로 마무리한다. 기동·healthcheck·스모크 실패 시 이전 구성으로 되돌린다.
Compose `.env`의 기존 설정은 유지하고 이미지·자료 버전만 갱신한다. `.env.django`는 교체하지 않는다. 코드 롤백은 `db/`를 건드리지 않는다.

생성 파일(Git 제외):

```text
dist/earththrutime3d-image-v0.14.1.tar.gz
dist/earththrutime3d-data-v0.14.1.tar.gz
dist/earththrutime3d-host-v0.14.1.tar.gz
dist/SHA256SUMS-v0.14.1
```

## dolfinid 최초 설치

2026-09-12 확인: SSH `dolfinid` → `honestjung@cdgts.paleobytes.info`, x86_64, Docker 29.8.0,
Compose 5.5.1. 기존 서비스와 분리해 `/srv/earththrutime3d`, **`127.0.0.1:8014`**를 쓴다.
확인 당시 8014는 비어 있었다.

빌드 호스트에서:

```bash
ssh dolfinid 'mkdir -p ~/earththrutime3d-release'
scp dist/earththrutime3d-*-v0.14.1.tar.gz dist/SHA256SUMS-v0.14.1 dolfinid:~/earththrutime3d-release/
```

서버에서:

```bash
cd ~/earththrutime3d-release
sha256sum -c SHA256SUMS-v0.14.1
docker load -i earththrutime3d-image-v0.14.1.tar.gz
sudo install -d -o "$(id -un)" -g "$(id -gn)" /srv/earththrutime3d
tar -xzf earththrutime3d-host-v0.14.1.tar.gz -C /srv/earththrutime3d
mkdir -p /srv/earththrutime3d/data/v0.14.1 /srv/earththrutime3d/db \
         /srv/earththrutime3d/backups /srv/earththrutime3d/acme
tar -xzf earththrutime3d-data-v0.14.1.tar.gz -C /srv/earththrutime3d/data/v0.14.1
cd /srv/earththrutime3d
cp .env.django.example .env.django && chmod 600 .env.django
# SECRET_KEY를 충분히 긴 무작위 값으로 바꾼다. 값은 출력하지 않는다.
sudo chown -R 10001:10001 db backups   # 컨테이너가 쓰는 유일한 경로
bash deploy.sh v0.14.1
```

Nginx는 ACME 검증을 위해 HTTP 전용 설정을 먼저 올리고, 인증서를 받은 뒤 전체 설정으로 바꾼다.

```bash
sudo certbot certonly --webroot --webroot-path /srv/earththrutime3d/acme \
  --domain earththrutime.nopeoplestime.info --cert-name earththrutime.nopeoplestime.info \
  --non-interactive --agree-tos --deploy-hook 'nginx -t && systemctl reload nginx'
```

도메인 없이 확인하려면 `ssh -L 18014:127.0.0.1:8014 dolfinid` 후 `http://localhost:18014/`를 연다.

## 오래된 버전 정리

`prune.sh`가 돌고 있는 버전과 되돌릴 수 있을 만큼의 이전 버전만 남기고 이미지·데이터
디렉터리·릴리스 묶음을 지운다. 기본 보존 개수는 2이며 `KEEP`으로 바꾸고, `DRY_RUN=1`로
먼저 확인한다. 이 서비스의 저장소 이름과 경로만 건드린다. 호스트에 다른 서비스가 여럿
돌고 있어 전역 정리는 하지 않는다.

## 접근 키

사이트 자체는 열려 있다. 키는 게시를 허락받지 못한 자료 하나를 여는 데만 쓴다.

이용 조건이 없는 판 모델은 목록 파일에 `publish: false`로 적는다. `ACCESS_KEY`가 설정된
배포에서는 드롭다운에 나오되 잠겨 있고, 고르면 그 자리에서 키를 묻는다. 화면을 떠나지
않으므로 보고 있던 시대와 시점이 그대로 남는다. 맞으면 세션에 기록해 30일 동안 묻지
않는다. `ACCESS_KEY`가 비어 있으면 그 모델은 목록에도 나오지 않고 경로도 404다.

계정이 아니다. 사용자도 없고 키를 가진 사람은 모두 같은 방문자다. 키는 상수 시간으로
비교하고, 돌아갈 주소는 내부 경로만 받는다.

## 백업

`backup.sh`는 일회용 컨테이너에서 sqlite3의 backup API로 스냅샷을 뜨고 무결성을 검사한다.
검사에 실패한 사본은 버린다. 믿게 되기 때문이다. 검증된 새 스냅샷이 생긴 뒤에만 오래된
것을 지우고, 최소 한 개는 남긴다. 기본 보관 개수는 14이며 `KEEP`으로 바꾼다.

`earththrutime3d-backup.timer`가 매시간 같은 명령을 돌린다. 배포 직전 스냅샷은 `deploy.sh`가
직접 실행한다.

원격지 사본은 개발 호스트 m710q가 매일 04:20에 만든다(`system-operation/m710q/backup-earththrutime.sh`).
여기 `backups/`의 검증된 최신 스냅샷과 `.env.django`를 당겨 날짜별로 보관하고(로컬 30일·NAS 90일),
개발 호스트의 `data/sources`와 최신 릴리스 묶음을 NAS에 미러하고, `data/derived`는 일(14일)·주(12주)·월(12개월, 12월분 영구) 스냅샷으로 보관한다. 자료가 DB가
아니라 파일이고 개발 호스트에서 만들어지므로 미러의 출발점은 서버가 아니라 개발 호스트다.

## 환경 변수

| 변수 | 역할 |
|---|---|
| `SECRET_KEY` | 50자 이상. 짧거나 비어 있으면 기동 거부 |
| `ALLOWED_HOSTS` | 명시 필수. 와일드카드 거부 |
| `DATABASE_PATH` | 이미지 기본 `/var/lib/earththrutime3d/db.sqlite3` |
| `ACCESS_KEY` | 비공개 자료를 여는 공유 키. 비우면 그 자료를 아예 제공하지 않는다 |
| `SCOTESE_VIEWER_ENABLED` | 뷰어 사용 여부 |
| `SCOTESE_SOURCE_MAPS_PUBLIC` | 원본 지도 제공 여부. 기본 꺼짐 |
| `MANTLE_DERIVED_DIR` | 이미지 기본 `/runtime/mantle/muller2022-opt1` |
| `INDIA_ASIA_DERIVED_DIR` | 이미지 기본 `/runtime/india-asia` |
| `SCOTESE_DERIVED_DIR` | 컨테이너 기본 `/runtime/segmentation` |
| `SCOTESE_VIEWER_STEPS` | 지도 사이 눈금 수. 1·2·4·8·16·32 |
| `SCOTESE_VIEWER_INTERVAL_MA` | 대신 몇 백만 년마다 눈금을 둘지 |
| `TRUST_PROXY_HEADERS` | 앞단 프록시가 전달 헤더를 정리할 때만 참 |
| `SECURE_SSL_REDIRECT` | 호스트 Nginx가 이미 돌려보내므로 거짓 |
| `GUNICORN_WORKERS`, `GUNICORN_THREADS` | 각각 2, 4 |
| `HOST_PORT` | 배포 스크립트 기본 8014. 바꾸면 Nginx도 맞춘다 |

## 업데이트 중 안내

Nginx가 502·503·504를 받으면 `/srv/earththrutime3d/maintenance.html`을 503으로 제공한다.
10초마다 다시 시도하며 `Retry-After: 10`과 `Cache-Control: no-store`를 보낸다. HTML은 호스트
묶음에 있어 컨테이너 교체 중에도 제공된다.
