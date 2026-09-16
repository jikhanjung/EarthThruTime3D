# OPT1 GPU 재현·이식 실행 계획

작성일: 2026-09-16  
대상: Müller et al. (2022)의 OPT1 mantle convection 모델  
실행 환경: 사용자 대화 기준 Quadro RTX 8000 48 GB ×2, i7-7820X, 시스템 RAM 96 GB. 실제 장비·메모리·연결 상태는 착수 시 확인한다.

## 1. 목표와 판단 원칙

먼저 논문이 사용한 EarthByte CitcomS 계열에서 OPT1의 재현 기준을 만든다. 그 기준을 이용해 GPU Stokes 계산의 정확도·메모리·전체 실행시간을 검증한 다음, 물리 모델과 시간 의존 자료 동화(assimilation)를 이식하고 1000 Ma부터 현재까지 계산한다.

완료 목표는 두 가지로 구분한다.

- **원본 재현:** 논문에 대응하는 코드·입력·전처리·수치 설정으로 CitcomS 결과를 재현한다. 정확한 당시 커밋이 없으면 재현 범위를 명시한다.
- **GPU 이식:** 동일한 물리와 경계 자료를 다른 실행 경로나 수치기법으로 계산한다. 요소·격자·안정화·이류법이 달라지는 경우 bit-for-bit 재현을 요구하지 않고, 오차와 격자 수렴을 입증한다.

이 문서는 실행 계획이다. 서버 접속, 코드 빌드, 대용량 데이터 다운로드, benchmark 및 full run은 아직 수행하지 않았다. 이전 대화에 제시된 수 주~수개월 실행시간과 메모리 예상은 실측 근거가 없으므로 일정·용량 보증으로 사용하지 않는다.

### 근거 표시

| 표시 | 의미 |
|---|---|
| **[논문 확인]** | 업로드된 `se-13-1127-2022.pdf`에서 직접 확인. 주로 §2.2, 인쇄 p.1131 및 Table 1, p.1133 |
| **[공개 자료 확인]** | 공식 저장소·데이터 목록·문서에서 확인. 자료가 실제 완전하게 실행되는지는 별도 검증 |
| **[대화 정보]** | 사용자 환경에 관한 이전 대화 정보. 원격 서버에서 검증하지 않음 |
| **[계획/제안]** | 본 프로젝트의 작업 순서·예시 격자·합격 기준. 논문 설정이 아님 |
| **[미확인]** | 입력·소스 대조 또는 실측이 필요한 사항 |

## 2. OPT1 설정 기준표

아래 물리 값은 첨부 논문 §2.2와 Table 1에서 확인했다. 실행용 값은 공개 입력과 소스를 대조한 뒤 확정한다. 충돌 시 임의로 한쪽을 선택하지 말고 차이와 선택 이유를 기록한다. [원 논문](https://doi.org/10.5194/se-13-1127-2022)

| 항목 | 논문에서 확인된 값·방법 | 이식 시 확인할 사항 |
|---|---|---|
| 지배 모델 | Extended Boussinesq approximation, 수정 CitcomS | 실제 활성화된 에너지·기준상태 항을 소스에서 확인 |
| 영역 | 3차원 전 지구 구각; 지구 반경 6371 km, 핵 반경 3504 km, 맨틀 두께 2867 km | 좌표, Jacobian, 중력 방향, 무차원 길이 척도 |
| 격자 | 약 13M nodes: 129×129×65×12, 반경 방향 비균일 격자 | cap 경계 중복·ghost를 제외한 고유 node와 속도·압력 DOF 집계 |
| 공간 해상도 | 표면 약 50×50×15 km, CMB 약 28×28×27 km, 중부 약 40×40×100 km | 원 반경 격자 파일 보존 |
| Rayleigh 수 | 7.8×10^7 | 맨틀 두께로 정의된 Ra와 코드 길이 척도의 차이 |
| Dissipation 수 | 1.56 | 정의에 지구 반경 R0 사용; Ra와 동일 길이를 쓰는 것으로 가정하지 않음 |
| 표면/CMB 온도 | 273 K / 3373 K; ΔT=3100 K | 절대온도·무차원온도·potential temperature 변환 |
| 속도 경계 | 표면은 재구성 plate velocity, CMB는 free slip | 관통 불가 조건, 구면 성분, 회전 기준계 |
| 열물성 기준 | α0=3×10^-5 K^-1, ρ0=4000 kg m^-3, g0=9.81 m s^-2 | 깊이별 reference-state 물성은 별도 파일 대조 |
| 열확산/비열 | κ0=10^-6 m² s^-1, Cp0=1200 J kg^-1 K^-1 | 열전도율·열원 단위 변환 |
| 내부 가열 | 전체 모델 33.6 TW | 공간 분배를 확인하고 체적 적분으로 총량 검증 |
| 기저 조성층 | 초기 두께 113 km | tracer 생성, 초기 체적·질량 및 계면 표현 |
| OPT1 부력비 | B=0.25; B=δρch/(ραΔT) | OPT2 등의 B=0.325와 혼동 금지 |
| 기저 밀도 증가 | 약 1%; δρch=56.8 kg m^-3 | 이 설명에 사용된 CMB 부근 값은 ρ=5546 kg m^-3, α=1.32×10^-5 K^-1. 표면 기준값으로 다시 계산해 덮어쓰지 않음 |
| 기준 점성 | η0=1.1×10^21 Pa s | 점성식의 기준점 및 clip 설정 확인 |
| 깊이별 점성 계수 | 160 km 위 0.02; 160–310 km 0.002; 310–660 km 0.02; 660 km 아래 0.2 | 경계에서 보간·불연속 처리 확인 |
| 조성별 점성 계수 | 주변 맨틀 1, 대륙 암석권 100, 기저층 10 | 혼합법 및 시간에 따른 조성 추적 확인 |
| 온도·압력 의존 점성 | 활성화 에너지 283.5 kJ mol^-1, 활성화 부피 2.1 cm³ mol^-1, Toff=496 K | 논문 지수식 전체를 코드와 대조; 단순 온도 지수식으로 대체하지 않음 |
| 조성 추적 | ratio tracer method | tracer 수·재분배·보간·난수 seed는 미확인 |
| 해저 연령 | half-space cooling, 최대 연령 80 Myr | 대륙 및 결측 영역 처리와 동화 mask 확인 |
| 진행 중 slab 동화 | 표면~350 km, dip 45°, 해저 연령 자료 1 Myr 간격 | 자료 간격은 solver timestep이 아님 |
| 초기 slab | 표면~1000 km; 425 km 위 dip 45°, 아래 90° | 진행 중 350 km 동화와 별도 구현 |
| 준비 계산 | 1000 Ma plate configuration을 적용한 250 Myr warm-up | 초기장 구성·동화 순서·plate forcing 적용 방식 확인 |
| 본 계산 | 1000 Ma → 0 Ma | warm-up과 합쳐 약 1250 Myr 적분 구간; 가변 timestep 수는 미확인 |

**[미확인]** 당시 실행 커밋, 컴파일 옵션, solver tolerance, 점성 상·하한, timestep 제한, tracer 수, MPI 분할, restart 형식, 모든 초기장과 입력의 완전성, 실제 소요시간. 논문 Table 1만으로 실행 설정이 완성되지는 않는다.

## 3. 단계별 실행 계획

순서: **장비 확인 → 공개 자료 확보 → 원본 빌드 → 저해상도 CPU baseline → frozen Stokes snapshot → GPU 후보 실험 → 물리 이식 → 자료 동화 이식 → 교차 검증 → full run**.

### 단계 0. 장비·실행 환경 확정

**목표:** 실측 가능한 성능 기준과 메모리 한도를 정한다.

**작업**

- 서버에서 GPU 모델·가용 VRAM, CPU 물리 코어, RAM, 저장 공간, 운영체제, 드라이버, CUDA 및 MPI 버전을 기록한다. 현재 문서를 작성하는 PC와 계산 서버를 구분한다.
- 두 GPU의 NVLink 브리지 설치 여부, 활성 링크, PCIe 배치, peer-to-peer 및 CUDA-aware MPI 동작을 확인한다. NVLink는 대화에서 언급됐지만 실제 연결은 미확인이다.
- GPU별 FP64 연산·메모리 대역폭·전송 성능을 간단히 측정한다. CPU oversubscription과 다른 작업의 영향을 기록한다.
- **[계획/제안]** 재현 가능한 Linux 환경을 우선 검토하되 설치 버전은 서버 호환성으로 결정한다.

**검증 기준:** CPU/MPI smoke test, 각 GPU 계산, GPU 간 전송이 동작하고 메모리·온도·오류 로그를 수집할 수 있다. 48 GB×2는 자동으로 하나의 96 GB 메모리가 되지 않는다. 분산 배치와 GPU별 peak VRAM을 검증해야 한다.

**산출물:** `environment.md`, `hardware_inventory.json`, 의존성·빌드 버전 목록, 장비 측정 로그.

### 단계 1. 공개 OPT1 input/data 확보 및 출처 고정

**목표:** 논문 재현에 필요한 자료와 누락 자료를 분리한다.

**작업**

- [Zenodo record 6622194](https://zenodo.org/records/6622194)의 `Input.zip`, `Pre-processing.zip`, README를 먼저 확보하고 원본을 변경 없이 보관한다.
- **[공개 자료 확인]** 목록에는 `OPT1.input`, 반경 격자 `G5.coor.global.dat`, reference state `new_2p5_6_T-H15_G5_di_formatted.dat`가 설명돼 있다. 전처리 설정은 `config-template.cfg`, `geodynamic_framework_defaults.conf`, 좌표 자료이며 `Create_History.py`와 연결된다.
- **[공개 자료 확인]** OPT1 온도 이상 NetCDF 출력과 해상도를 낮춘 ParaView 자료도 공개돼 있다. 온도 이상·시각화 파일을 완전한 restart로 간주하지 않는다.
- 압축 해제 후 입력 경로를 추적해 rotation, topology, coastline/continental mask, seafloor-age grid, plate velocity, slab history, tracer 자료가 1000–0 Ma 범위를 실제로 덮는지 검사한다.
- 모든 파일에 URL, 버전, 크기, checksum, 사용 권한, 원본/생성 자료 구분을 기록한다. 필요한 추가 plate model 자료의 출처는 원 논문 Code and data availability를 따른다.

**검증 기준:** 한 시점의 전처리가 외부의 미상 경로 없이 실행된다. 전체 시간 목록의 누락·중복을 검출한다. 원본 고해상도 T·C·η·속도·압력·tracer 상태가 없으면 “정확한 원본 snapshot 없음”으로 표시하고 단계 4에서 생성한다.

**산출물:** `data_manifest.csv`, 원본 자료 보관 영역, `missing_data.md`, 경로를 상대화한 전처리 설정.

### 단계 2. CitcomS 원본 실행 경로 재현

**목표:** 논문 비교 기준이 되는 CPU 코드를 고정한다.

**작업**

- 논문과 데이터 저장소가 지정한 [EarthByte/citcoms](https://github.com/EarthByte/citcoms)를 기준으로 한다. 일반 upstream 최신판을 동일 코드로 간주하지 않는다.
- 가능한 당시 커밋·분기·실행 설정을 조사하고, 확보하지 못하면 선택한 커밋과 알려진 차이를 기록한다. 기본 예제 실행 후 OPT1 입력을 단계적으로 연결한다.
- 논문 값, `OPT1.input`, 전처리 설정, 소스에서 실제 읽는 파라미터를 일대일 대응시킨다. 오래된 옵션의 무시·기본값 대체 여부를 로그로 확인한다.
- full-sphere의 12-cap 분할 제약과 필요한 MPI rank 수를 확인한다. CPU가 8코어라고 무조건 8-rank 실행을 가정하지 않는다. 더 많은 rank가 필요하면 oversubscription 비용을 기록한다.
- 과거 CUDA 구현 흔적은 별도 조사 항목이다. 해당 assimilation 코드와 현대 드라이버에서 검증되기 전에는 GPU 실행 경로로 채택하지 않는다.

**검증 기준:** 기본 예제 및 작은 구각 문제가 수렴하고 재시작된다. OPT1 옵션이 의도대로 반영됐다는 로그가 있다. 정확한 역사적 커밋이 없으면 결과를 “공개 코드 기반 재현”으로 명명한다.

**산출물:** 커밋 고정 소스, 빌드 절차, `OPT1_parameter_audit.csv`, 예제·restart 로그.

### 단계 3. 저해상도 CPU baseline

**목표:** GPU 개발 전에 전 지구 물리·동화·출력이 연결된 기준 계산을 확보한다.

**작업**

- **[계획/제안]** `33×33×17×12` → `65×65×33×12` → 원 격자 순의 해상도 사다리를 검토한다. 실제 지원하는 multigrid 계층과 분할 제약에 맞춰 조정한다.
- 해상도를 낮춰도 구각 전체, OPT1 B, 경계조건, 점성식, plate history를 유지한다. 113 km 층이 거친 격자에서 제대로 표현되는지 반경 격자·tracer 분포를 따로 점검한다.
- 짧은 warm-up·수십 timestep으로 smoke test를 한 후, 저해상도에서 250 Myr warm-up과 본 계산 초기 구간을 수행한다. 짧은 시험을 완전한 초기조건 생성으로 부르지 않는다.
- Stokes, 점성 갱신·조립, 열 이류·확산, tracer, 동화, I/O 시간을 분리해 기록한다. 실제 병목 비율을 측정한다.

**검증 기준:** NaN·발산·잘못된 경계온도가 없고 재시작 전후 결과가 solver 오차 범위에서 이어진다. 열·조성 수지에는 동화로 주입·제거한 양을 별도로 반영한다. 격자를 늘렸을 때 주요 진단량이 수렴 경향을 보인다.

**산출물:** 저해상도 설정 2종 이상, 초기 상태·checkpoint, `cpu_baseline.csv`, 열수지·조성량·RMS velocity 시계열.

### 단계 4. Single-snapshot 13M-node Stokes benchmark 구성

**목표:** 시간 진화와 분리한 대표 Stokes 문제로 GPU 이식의 첫 투자 판단을 한다.

**작업**

- 대표 시점 하나를 선정하고 격자, 온도, 조성, η, 부력 또는 우변, 표면 속도, CMB 조건과 reference state를 동결한다. 먼저 저해상도로 시험하고 중간 격자를 거쳐 약 13M-node 규모로 올린다.
- 정확한 원본 restart가 없으면 단계 3에서 생성하거나 고해상도 CitcomS 계산으로 snapshot을 만든다. 저해상도장을 보간한 경우 “성능 시험용 구성 snapshot”으로 표기한다. 공개 온도 이상만으로 절대온도·조성을 복원했다고 주장하지 않는다.
- **A: 동일 선형계 비교.** 가능하면 CitcomS의 이산 연산자·우변·경계 처리·압력 nullspace를 보존해 CPU/PETSc CPU/GPU를 비교한다. 행렬 추출을 위해 추가 개발이 필요한지 먼저 조사한다.
- **B: 동일 연속문제 비교.** GAUZZ 등 다른 요소를 쓰면 동일 물성·경계를 제공하되 격자 및 공통 오차 수준을 맞춘다. A와 B의 성능 결과는 별도로 보고한다.
- 압력 기준을 맞추고, Stokes 구속조건·강체 회전 nullspace의 존재를 실제 경계조건으로 판단한다. η 동결 시험 이후에는 점성 갱신·조립이 포함된 시험도 추가한다.
- CPU 최초 setup과 반복 solve, GPU 최초 전송·AMG setup과 재사용 solve를 구분한다. **[계획/제안]** warm-up 실행 후 동일 조건 3회 이상 측정해 중앙값·범위를 기록한다.

**검증 기준:** 동일 정확도에서 해·잔차·비압축성 오차를 비교할 수 있고, 초기 setup을 포함한 시간도 제공한다. GPU 실패/OOM도 결과로 기록한다. 13M nodes는 13M DOF가 아니며 속도 3성분·압력·요소 선택에 따라 시스템 크기가 달라진다.

**산출물:** `snapshot_manifest.json`, 재현 가능한 benchmark driver, CPU 기준 해, DOF·nonzero·iteration·wall-time·RAM/VRAM 결과표.

### 단계 5. GPU 후보 비교 및 1→2 GPU 실험

**목표:** 구현 가능성과 실측 성능으로 이식 경로를 선택한다.

| 후보 | 확인된 출발점 | OPT1 이식에서 검증할 공백 | 프로젝트 내 역할 |
|---|---|---|---|
| EarthByte CitcomS CPU/MPI | 논문이 지정한 assimilation 계열 | 당시 커밋·입력 완전성 | 원본 기준 |
| CitcomS + PETSc/CUDA adapter | PETSc에 CUDA 행렬·벡터 경로 존재 | 원 연산자 연결, 분산 전처리, GPU에 남는 연산 범위 | 기존 물리·동화 보존을 위한 후보 |
| GAUZZ류 FEniCS/PETSc/CUDA | GPU Stokes 연구 구현과 benchmark 공개 | 구각, 13M 규모, tracer·열방정식, OPT1 동화, 의존성 재현 | 우선 소규모 GPU 실험 후보 |
| ASPECT | 맨틀 대류 프레임워크와 geometric multigrid 문서 | 선택 버전의 실제 GPU Stokes 경로·기능 지원, 동화 플러그인 | 물리 이식 및 CPU 비교 후보 |
| Underworld3 | 공개 지구동역학 코드 | 선택 backend의 GPU 실행·구각·동화 구현과 메모리 | 보조 후보 |
| LaMEM | 공개 3D 지구동역학 코드 | OPT1 전 지구 구각 적합성, GPU 경로·동화 구현 | 우선순위 낮은 보조 후보 |

공식 근거: [PETSc GPU roadmap](https://petsc.org/release/overview/gpu_roadmap/), [GAUZZ preprint](https://doi.org/10.5194/egusphere-2026-2528), [ASPECT](https://aspect.geodynamics.org/), [ASPECT GMG](https://aspect-documentation.readthedocs.io/en/latest/user/methods/geometric-multigrid.html), [Underworld3](https://github.com/underworldcode/underworld3), [LaMEM](https://github.com/UniMainzGeo/LaMEM).

**GAUZZ 해석:** 확인한 자료는 2026년 preprint이다. 초록의 5–11배는 pressure-correction 관련 execution time이며, 비선형 점성 사례의 single-GPU 전체 wall-time 개선은 1.14–3.46배로 구분된다. 두 GPU 사례의 5.83배 역시 해당 실험 조건의 결과다. 이를 RTX 8000의 OPT1 성능 예측에 대입하지 않는다. [GAUZZ 원문](https://doi.org/10.5194/egusphere-2026-2528)

**작업**

- GAUZZ의 코드·보충자료·라이선스·버전을 확보하고 제공 예제를 먼저 재현한다. 제공 예제 성공을 구각 OPT1 지원의 증거로 대신하지 않는다.
- PETSc CUDA 벡터/행렬뿐 아니라 preconditioner, assembly, coarse solve, halo exchange의 실행 위치를 profiler로 확인한다. PETSc를 사용한다는 사실만으로 응용 코드 전체가 GPU화되지는 않는다.
- FP64를 초기 기준으로 한다. mixed precision은 잔차 재계산·보정과 단계 8 검증을 통과한 뒤 선택한다.
- 한 GPU에 들어가는 동일 문제로 1→2 GPU strong scaling을 측정한다. 두 GPU에서만 들어가는 큰 문제는 capacity 확장 성과로 따로 보고한다.
- mesh·tracer·행렬·AMG 계층·Krylov 벡터·임시 복사본·MPI buffer의 peak 메모리를 측정한다. CUDA 할당량과 시스템 RAM을 함께 기록한다.

**검증 기준 및 결정**

- **[계획/제안]** 각 GPU에서 가용 VRAM의 약 15–20% 여유를 목표로 한다. 초기 비싼 setup 시점도 포함한다.
- **[계획/제안]** 정확도를 유지하면서 전체 timestep에 가까운 측정의 2배 이상 가속을 우선 채택 기준으로 둔다. 1–2배는 개발·운영 비용과 비교해 조건부 채택, 1배 이하는 병목 개선 후 재평가한다. 이는 논문 기준이 아니다.
- 13M에서 메모리가 부족하면 matrix-free/다른 전처리/더 큰 장비를 검토한다. 해상도를 낮춰 종료하면 “원 해상도 OPT1 완료”로 표시하지 않는다.

**산출물:** `solver_comparison.md`, 고정 빌드 설정, profiler 결과, `gpu_benchmark.csv`, 채택·보류 결정서.

### 단계 6. OPT1 물리 파라미터 이식

**목표:** 선택한 GPU 경로에서 동일 물리 항과 초기조건을 구현한다.

**작업**

- 기준표를 실행 가능한 parameter mapping으로 옮긴다. 각 값에 원 입력 키, SI 단위, 무차원 값, 대상 코드 키, 근거를 붙인다.
- 반경별 reference state와 extended-Boussinesq 에너지 항을 대조한다. 단순 Boussinesq를 임시로 쓰면 검증용 축약 모델이라고 명명한다.
- 점성의 깊이·온도·조성 의존성, 기준점, clipping·혼합 규칙을 보존한다. 대표 깊이·온도·조성 점에서 원 코드와 직접 비교한다.
- basal layer와 continental lithosphere의 조성·점성 영향을 분리하고 tracer 이동·재구성 오차를 측정한다.
- 내부 가열은 입력 단위를 변환한 뒤 영역 적분이 33.6 TW에 대응하는지 확인한다. 밀도 관련 reference 값의 용도를 혼합하지 않는다.

**검증 기준:** η·부력·열원 단위 시험을 통과한다. 같은 물성장·격자에서 Stokes 결과가 단계 8 기준을 만족한다. basal layer 초기 두께와 적분 조성량이 격자 오차 안에서 보존된다.

**산출물:** `physics_mapping.csv`, 물성 함수 검증 결과, `OPT1_gpu` 설정, 원 코드 대비 차이 목록.

### 단계 7. Plate / seafloor-age / slab assimilation pipeline 이식

**목표:** 원본 OPT1의 시간 의존 외부 forcing을 동일하게 공급한다.

**작업**

- 전처리와 solver를 분리하고 공통 포맷에 시각, 단위, 좌표계, plate ID, mask, 출처를 포함한다. 처음에는 원 전처리 출력을 읽는 adapter를 우선한다.
- plate rotation·velocity의 기준계, 시간 방향, 위도/여위도, 경도 wrapping, 구면/Cartesian 벡터 변환을 검증한다. OPT1을 임의로 no-net-rotation 모델로 바꾸지 않는다.
- `age_Ma = 1000 - elapsed_main_Myr` 관계를 명시하고 warm-up의 시간을 별도로 관리한다. 1 Myr 자료와 가변 solver timestep 사이 보간 규칙을 원 구현과 맞춘다.
- seafloor-age 상한 80 Myr와 half-space cooling을 구현한다. 대륙·결측·해구 경계에서 thermal field를 어떻게 정의하는지 원 설정을 따른다.
- 초기 1000 km slab과 진행 중 350 km slab을 서로 다른 단계로 구현한다. slab polarity·dip·중첩·두께·동화 가중치·온도 덮어쓰기 순서는 전처리와 소스를 확인한다.
- 12-cap 경계, 날짜 경계선, 극점, plate ID 변경 및 topology event에서 위치·벡터·온도 연속성을 검사한다.
- 먼저 고정 시점, 다음 여러 시점, 마지막으로 전체 1000–0 Ma 자료를 검사한다. **[계획/제안]** 1000, 750, 500, 250, 0 Ma와 topology 변화 직전·직후를 표본으로 삼는다.

**검증 기준:** 같은 공통 표본점에서 원 전처리와 plate velocity·age·thermal/slab mask가 일치하거나 설명 가능한 보간 오차 안에 있다. 시간 누락이 없고, 동화 열·조성 수지를 분리 기록한다. 국부 mask 경계의 차이를 전체 평균에 숨기지 않는다.

**산출물:** forcing adapter, `assimilation_mapping.md`, 전처리 재실행 절차, 시점별 비교 지도·오차표.

### 단계 8. CPU-vs-GPU 정확도 및 과학적 검증

**목표:** 하드웨어 차이, 수치기법 차이, 장시간 물리 차이를 구분한다.

아래 수치는 모두 **[계획/제안]**이다. 기준 계산의 오차·solver tolerance·격자 수렴을 확인한 뒤 본 계산 전에 확정하며, 실패 결과에 맞춰 사후 완화하지 않는다.

| 비교 수준 | 시험 | 초기 합격 기준 제안 |
|---|---|---|
| 동일 이산 문제 CPU/GPU | FP64 frozen Stokes | 실제 재계산 상대 잔차 ≤10^-8을 시작점으로 검토; 속도 상대 L2 차이 ≤10^-6. 압력은 평균 제거 후 비교 |
| 연속방정식 잔차 | 질량·운동량 | 비압축성 또는 원 reference-state 질량식을 동일한 무차원 norm으로 평가. CPU 기준보다 유의하게 악화되지 않음 |
| 다른 요소/solver | manufactured solution, 구각 Stokes, 동일 OPT1 snapshot | 공통 격자로 투영한 속도 오차 1% 이내를 초기 목표로 하고, 더 엄격한 격자 수렴 오차가 확인되면 그 기준 사용 |
| 짧은 결합 계산 | 공통 초기장·forcing·timestep | RMS velocity, 평균 T, 열유량 차이 1% 이내 목표. T·C 공간 오차 및 이류 오차도 보고 |
| 장시간·해상도 비교 | warm-up, 대표 구간, 최종 상태 | 열수지, 조성 수지, 온도 이상 패턴·깊이 프로파일·기저 구조가 CPU 해상도 연구의 허용 범위 안에 있음 |
| 재시작 | 중단 없이 계산 vs checkpoint 재개 | 짧은 구간에서 해당 solver의 수치 오차 범위 내 일치 |

**작업**

- 상대 norm의 분모가 거의 0인 장에는 절대 오차 척도를 별도로 정의한다. residual만 작고 잘못된 경계를 푼 경우를 걸러내기 위해 경계·물리 진단을 함께 확인한다.
- 서로 다른 수치기법의 경우 같은 node 수보다 같은 오차 수준에서 성능을 비교한다. 압력 공간·정규화 차이와 투영 오차를 명시한다.
- 공개 OPT1 출력과 동일 시각·깊이·온도 이상 정의·필터를 맞춰 비교한다. 저해상도 시각화만으로 고해상도 일치를 주장하지 않는다.
- 장시간의 비선형 발산은 단일 cell 일치 대신 수렴 연구와 패턴·통계로 평가한다. 논문의 과학적 재현까지 주장하려면 §2.3의 BMS cluster 및 tomography/volcanism 비교 지표도 같은 처리로 재계산한다.

**검증 기준:** 성능 개선과 정확도 합격을 동시에 만족한다. 불일치는 물리, forcing, 수치기법, 정밀도, 자료 결손 중 원인을 분류한다. 해결되지 않은 차이는 full-run 진입 전에 범위를 명시한다.

**산출물:** `validation_report.md`, 오차·격자 수렴표, CPU/GPU 비교 그림, 확정 허용 기준.

### 단계 9. Full 1 Ga run 및 결과 공개 준비

**목표:** 검증된 구성으로 250 Myr warm-up 후 1000–0 Ma OPT1 계산을 완료한다.

**작업**

- 최종 해상도에서 짧은 pilot을 수행하고 초기·고점성 대비·빠른 plate motion 구간을 표본 측정한다. 준비 계산과 본 계산의 비용을 따로 추정한다.
- full run에는 검증된 250 Myr warm-up 상태를 사용한다. 낮은 해상도 warm-up을 보간해 쓰면 원본 절차와의 차이를 별도 검증하고 기록한다.
- 평균 timestep을 임의로 0.1 또는 1 Myr로 고정하지 않는다. 측정된 Δt 분포와 timestep 비용으로 소요시간을 예측한다.
- checkpoint에 T, C/tracer, 시간, forcing index, 필요한 reference state, solver 재개 정보와 난수 상태를 담고 실제 재시작을 시험한다.
- 저장 용량은 checkpoint 크기×보존 개수, 출력 크기×시점 수, 전처리 cache, 임시 공간으로 산정한다. 출력 간격과 보존 정책은 이 예산에 맞춘다.
- 1000→750→500→250→0 Ma 등 구간 완료 시 수렴·열수지·조성·peak memory를 점검한다. 구간 구분은 운영 제안이며 물리 forcing을 초기화하는 지점이 아니다.

**검증 기준:** 현재 시점까지 도달하고 누락 출력·NaN·미해결 solver 실패가 없다. 최종·중간 결과가 단계 8의 기준을 만족한다. 전체 CPU 대조 run을 하지 못했다면 검증한 시간·해상도 범위를 명시한다.

**산출물:** 전체 시계열, checkpoint·restart 절차, `full_run_report.md`, 파라미터·코드·데이터 manifest, 재현용 공개 패키지 초안.

## 4. 메모리·시간 예산 산정법

### 메모리

**[계산 예시]** 논문 격자 곱은 12,979,980이다. 경계 중복을 무시한 이 개수의 FP64 scalar 한 개는 약 104 MB, 속도 3성분은 약 312 MB이다. 이것은 일부 field 저장량일 뿐이다. sparse matrix, 압력, AMG 계층, Krylov basis, tracer, ghost 및 조립 버퍼를 포함한 전체 메모리를 뜻하지 않는다.

측정할 예산:

```text
peak VRAM per GPU = local fields + local matrix/operators + preconditioner
                  + Krylov workspace + ghost/communication + temporary allocations
peak host RAM     = mesh/tracers + assembly + host copies + I/O/MPI buffers
```

**[미확인]** 실제 nonzero 수·AMG operator complexity·분할 불균형이 없으므로 13M 문제의 2×48 GB 수용 여부를 현재 확정할 수 없다. 행렬을 명시적으로 조립하는 다른 solver는 CitcomS보다 메모리를 훨씬 많이 쓸 수도 있다.

### 실행시간

```text
T_total = T_preprocess + T_warmup
        + Σ (T_viscosity/assembly + T_Stokes + T_energy + T_tracer
             + T_assimilation + T_communication + T_IO)
```

GPU 가속은 `S = CPU wall time / GPU wall time`으로 정의하고 측정 구간을 함께 적는다. Stokes 비율이 f, 그 부분의 가속이 s일 때 이론적 전체 가속 상한의 단순 추정은 `1 / ((1-f) + f/s)`이다. 추가 GPU 통신·전송 비용은 이 식에 별도로 반영해야 한다.

**[계산 예시, 예측 아님]** f=0.8, s=5라면 추가 비용이 없어도 전체는 약 2.78배다. 따라서 GAUZZ의 부분 solver 가속률을 full 1 Ga 계산의 가속률로 사용하지 않는다.

개발 일정은 데이터 완전성·구각 이식 난도에 좌우된다. “며칠 안에 13M benchmark 완료”를 약속하지 않고, 단계별 산출물과 통과 기준으로 진행을 관리한다.

## 5. 진행·중단 판단표

| 관문 | 다음 단계 진행 조건 | 실패 시 경로 |
|---|---|---|
| G0: 자료·원본 | 필요한 입력과 작은 CPU 계산 확보 | 누락 자료 조사; 불완전 재현 범위 명시 |
| G1: benchmark | 신뢰 가능한 frozen snapshot과 CPU 기준 해 | snapshot 생성 또는 작은 구각 검증부터 수행 |
| G2: GPU 채택 | 정확도·메모리·전체 시간 기준 통과 | 전처리/행렬 구조 개선, CPU 유지, 외부 HPC 검토 |
| G3: 결합 모델 | 물리·동화·짧은 시간 진화 검증 통과 | forcing 및 수치기법 차이를 해결 |
| G4: 장기 계산 | restart·용량·시간 예산과 최종 해상도 pilot 통과 | 해상도/장비/범위 재설정 후 검증 반복 |

## 6. 첫 실행 묶음

- [ ] 장비 inventory와 NVLink/P2P 상태 확인.
- [ ] 입력·전처리 archive 확보 및 파일별 manifest 작성.
- [ ] EarthByte CitcomS 커밋 고정, OPT1 파라미터 대조.
- [ ] 저해상도 full-sphere CPU 실행과 restart 검증.
- [ ] 작은 frozen Stokes snapshot 생성 및 공통 norm 정의.
- [ ] GAUZZ 제공 예제와 PETSc CUDA 경로를 각각 재현.
- [ ] 같은 정확도에서 CPU/1 GPU/2 GPU 시간을 측정.
- [ ] 중간 격자 메모리로 13M 실험 진입 가능성 판단.

## 7. 참고 자료와 확인 범위

1. **첨부 원 논문:** Müller et al. (2022), *A tectonic-rules-based mantle reference frame since 1 billion years ago – implications for supercontinent cycles and plate–mantle system evolution*. 업로드 PDF §2.2, Table 1을 직접 읽어 물리 값을 확인. [논문](https://doi.org/10.5194/se-13-1127-2022)
2. **공개 OPT1 자료:** 파일 목록과 설명을 확인했으며 archive 내부 전체와 실행 가능성은 아직 검증하지 않음. [Zenodo](https://zenodo.org/records/6622194)
3. **원본 계열 코드:** assimilation 버전 및 전처리 출발점. [EarthByte CitcomS](https://github.com/EarthByte/citcoms), [전처리 경로](https://github.com/EarthByte/citcoms/tree/master/pre_post_processing)
4. **GPU 구현 후보:** 연구 결과의 존재와 성능 측정 범위를 확인했으며 OPT1 지원은 미검증. [GAUZZ preprint](https://doi.org/10.5194/egusphere-2026-2528)
5. **라이브러리 GPU 지원:** 응용 코드 전체 가속을 보장하지 않음. [PETSc GPU roadmap](https://petsc.org/release/overview/gpu_roadmap/)
6. **대체 코드:** 선택 버전과 실제 GPU 실행 경로는 후보 시험에서 확정. [ASPECT](https://aspect.geodynamics.org/), [Underworld3](https://github.com/underworldcode/underworld3), [LaMEM](https://github.com/UniMainzGeo/LaMEM)

이 문서에 나오는 향후 산출물 파일명은 계획상의 이름이다. 이번에 작성한 산출물은 이 Markdown 문서 하나다.
