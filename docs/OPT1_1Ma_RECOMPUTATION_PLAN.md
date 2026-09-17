# OPT1 1 Ma 재계산 및 EarthThruTime3D 통합 계획

## 1. 목적

Müller et al. (2022)의 **OPT1 mantle-flow model**을 가능한 한 원 논문과
동일한 조건으로 재계산하고, 기존 공개 결과의 20 Ma 간격보다 촘촘한 **1
Ma output cadence**로 mantle visualization 자료를 생성하여
**EarthThruTime3D**에 통합한다.

핵심 원칙:

-   **1 Ma는 numerical timestep이 아니라 output cadence**이다.
-   우선 GPU 포팅보다 **원본 CitcomS CPU/MPI 모델의 재현성 확보**에
    집중한다.
-   전체 1 Ga 계산 전에 짧은 구간을 원해상도로 계산하여 wall time, RAM,
    I/O를 실측한다.
-   공개된 20 Ma OPT1 결과를 검증용 keyframe으로 사용한다.
-   1 Ma마다 full simulation state를 저장하기보다 EarthThruTime3D에
    필요한 파생 자료를 우선 저장한다.
-   GPU/HPC 전환 여부는 benchmark 후 결정한다.

## 2. 기준 모델: OPT1

논문에서 확인되는 주요 조건:

  -----------------------------------------------------------------------
  항목                                설정
  ----------------------------------- -----------------------------------
  Solver                              CitcomS

  Geometry                            3-D spherical mantle

  Approximation                       Extended Boussinesq

  Grid                                129 × 129 × 65 × 12

  Nodes                               약 13 million

  Mantle thickness                    2867 km

  Basal layer                         113 km

  Buoyancy ratio                      B = 0.25

  Basal excess density                약 1%

  Reference viscosity                 1.1 × 10\^21 Pa s

  Rheology                            temperature-, depth-,
                                      composition-dependent viscosity

  Internal heating                    33.6 TW

  Initial slab depth                  1000 km

  Warm-up                             250 Myr at 1000 Ma configuration

  Production                          1000 Ma → present

  Surface forcing                     reconstructed plate velocities

  Lithosphere/slabs                   reconstructed seafloor ages 및
                                      time-dependent slab assimilation

  현재 공개 temperature product       주로 20 Ma cadence
  -----------------------------------------------------------------------

## 3. 최종 산출물

목표 시간축은 `1000, 999, 998, ... 2, 1, 0 Ma`, 총 **1001 frames**이다.

각 시점에서 우선 저장할 자료:

1.  selected-depth temperature anomaly
2.  basal mantle temperature anomaly
3.  필요 시 composition/basal-material mask
4.  필요 시 slab-related temperature field
5.  provenance 및 simulation metadata

### Checkpoint와 visualization output 분리

**Checkpoint** - restart용 full state - 5--20 Ma 정도의 성긴 간격 -
대용량 허용

**Visualization product** - EarthThruTime3D용 - selected depths/derived
fields - **1 Ma cadence** - 압축 및 웹 변환을 전제로 설계

## 4. 실행 환경

초기 대상:

``` text
CPU : Intel Core i7-7820X, 8C/16T
RAM : 96 GB
GPU : NVIDIA RTX 8000 48 GB ×2, NVLink
```

1차 계획은 **CPU/MPI CitcomS reproduction**이다. GPU는 초기 재현에
필수로 간주하지 않는다.

## 5. Phase 0 --- 공식 자료 확보 및 버전 고정

확보 대상:

-   OPT1.input
-   사용된 CitcomS source/version 및 수정 코드
-   radial mesh file
-   reference-state file
-   preprocessing configuration
-   plate velocity input
-   seafloor-age input
-   slab/lithosphere assimilation input
-   tracer initialization
-   공개 OPT1 temperature anomaly grids
-   공개 ParaView output
-   supplementary material

각 파일에 대해 source URL, download date, version/commit, SHA256,
filename을 기록한다.

권장 구조:

``` text
data/original/
config/original/
src/citcoms-original/
PROVENANCE.md
checksums.sha256
```

## 6. Phase 1 --- Build 및 smoke test

-   compiler/MPI 환경 확인
-   CitcomS build
-   bundled benchmark 실행
-   MPI rank별 성능 확인
-   restart/output test

7820X에서 우선 4/8 MPI ranks를 비교하고, SMT를 이용한 추가 rank가 실제
이득을 주는지도 실측한다.

성공 기준: - 정상 종료 - NaN/Inf 없음 - restart 성공 - 반복 결과가 허용
오차 내 일치

## 7. Phase 2 --- 저해상도 OPT1 reproduction

원해상도 전에 예를 들어 다음을 시험한다.

``` text
33 × 33 × 17 × 12
65 × 65 × 33 × 12
```

검증: - plate forcing - seafloor-age thermal structure - slab
assimilation - basal layer - tracers - viscosity - temperature
evolution - restart/output pipeline

정성적으로 다음 mantle evolution sequence가 나타나는지 확인한다.

``` text
1000–600 Ma : basal ridge network
600–500 Ma  : polar degree-2
500–400 Ma  : transition
400–200 Ma  : Pacific-centred degree-1
~160–0 Ma   : Pacific + African degree-2
```

## 8. Phase 3 --- 원해상도 short benchmark

원해상도:

``` text
129 × 129 × 65 × 12
≈ 12.98 million nodes
```

전체 1 Ga를 바로 돌리지 않고 가능한 경우 checkpoint/restart를 이용해
**10--20 Ma 구간**을 계산한다. 권장 pilot은 `100 → 80 Ma`.

측정 항목:

-   wall time
-   CPU utilization
-   peak RAM/swap
-   solver iterations
-   numerical timestep
-   timesteps per Myr
-   checkpoint size
-   1 Ma output I/O overhead
-   disk throughput

전체 production 시간은 실측 benchmark에서 추정한다. 현재 수
주\~수개월이라는 예상은 **추정치이며 benchmark로 확정**한다.

## 9. Phase 4 --- 공개 OPT1 keyframe 검증

재계산 결과를 공개된 20 Ma cadence 결과와 비교한다.

비교 항목: - temperature anomaly - spatial correlation - RMS
difference - mean/variance - basal mantle structure geometry - hot/cold
area fraction - plume/slab morphology

bit-for-bit equality보다는 numerical reproducibility와 large-scale
structure의 일치를 검증한다.

## 10. Phase 5 --- 1 Ma output cadence 구현

**중요:** timestep을 1 Ma로 만드는 것이 아니다. CitcomS의 안정성 조건에
따른 작은 numerical timestep으로 계속 적분하면서 geological clock이 1 Ma
output 시점을 통과할 때 visualization field를 export한다.

``` text
numerical timesteps
 | | | | | | | | | | |

100 Ma      99 Ma      98 Ma
  ↓           ↓          ↓
export      export      export
```

EarthThruTime3D에서 실제 사용하는 depth를 우선한다. 예:

-   \~2677 km: basal mantle
-   \~400 km: upper mantle
-   추가 selected depths

1 Ma full 3-D volume 저장은 필요성이 확인될 때만 수행한다.

## 11. 저장공간 계획

공개 20 Ma product 전체를 단순히 1 Ma로 확대하면 수십 GB가 될 수 있다.
그러나 selected-depth grids만 저장하면 훨씬 작다.

예를 들어 grid 하나가 약 0.8 MB라면:

``` text
1001 times × 5 depths × 0.8 MB ≈ 4 GB
```

이는 **추정치이며 실제 포맷과 compression으로 확정**한다.

권장 계층:

``` text
restart checkpoint      : 5–20 Ma
scientific derived grid : 1 Ma
web texture/tile        : 1 Ma
```

## 12. Phase 6 --- 1 Ma pilot run

`100 → 80 Ma`를 1 Ma output으로 계산하여 21 frames를 생성한다.

확인: - 1 Ma sequence의 temporal continuity - 100/80 Ma 공개 keyframe과
연결 - artificial flickering 여부 - storage/I/O overhead -
EarthThruTime3D에서 실제 시각적 개선

이 단계 성공 후 full production으로 간다.

## 13. Phase 7 --- Full production

### A. 처음부터

`250 Myr warm-up → 1000 Ma initial state → 0 Ma`

재현성은 가장 높지만 계산 비용이 크다.

### B. validated checkpoint restart

공개 또는 검증된 checkpoint가 있다면 restart하여 1 Ma output을 생성한다.
가능하면 이 경로를 우선한다.

권장 checkpoint 정책 예:

``` text
full restart checkpoint : 10 Ma
visualization output     : 1 Ma
```

## 14. QA

### Numerical

-   convergence
-   timestep stability
-   temperature behavior
-   viscosity bounds
-   tracer conservation
-   restart consistency

### Spatial

공개 20 Ma OPT1과 correlation/RMS/BMS geometry/major plume 및 slab 위치
비교.

### Temporal

1 Ma sequence에서 flickering, discontinuity, restart artifacts를
검사한다.

## 15. EarthThruTime3D 후처리

``` text
CitcomS
  ↓
1 Ma scientific output
  ↓
selected-depth extraction
  ↓
temperature anomaly normalization
  ↓
lat/lon raster
  ↓
quantization/compression
  ↓
EarthThruTime3D asset
```

권장 metadata 예:

``` json
{
  "model": "Muller_et_al_2022_OPT1_recomputed",
  "age_ma": 347,
  "field": "temperature_anomaly",
  "depth_km": 2677,
  "temporal_resolution_ma": 1,
  "source_model": "OPT1",
  "solver": "CitcomS",
  "recomputed": true
}
```

## 16. EarthThruTime3D 통합

서버에는 1 Ma scientific keyframes를 둔다.

``` text
mantle/opt1/2677km/0000
mantle/opt1/2677km/0001
...
mantle/opt1/2677km/1000
```

비정수 age에서는 인접한 두 1 Ma field를 GPU shader에서 interpolation할
수 있다.

``` text
scientific temporal resolution : 1 Ma
visual temporal resolution     : continuous
```

## 17. GPU/HPC 전환 기준

원해상도 20 Ma benchmark 이후 결정한다.

예시:

``` text
예상 full production < ~1 month  → X299 CPU 적극 고려
~1–2 months                      → X299 vs HPC 비교
> ~2 months                      → HPC/GPU 경로 우선 검토
```

또한 96 GB에서 swap이 발생하거나 메모리 안정성이 부족하면 HPC를
검토한다.

GPU 후보: 1. CitcomS의 기존 CUDA path 평가 2. PETSc/CUDA Stokes
benchmark 3. 현대 solver equivalent model 4. 외부 HPC allocation

GPU 이식은 numerical formulation 변화가 생길 수 있으므로 단순 성능
최적화가 아니라 별도 scientific validation 대상으로 취급한다.

## 18. 전체 실행 순서

``` text
원본 확보/고정
    ↓
CitcomS build
    ↓
smoke test
    ↓
저해상도 OPT1
    ↓
13M-node short benchmark
    ↓
공개 20 Ma 결과 검증
    ↓
1 Ma pilot output
    ↓
EarthThruTime3D pilot
    ↓
wall-time/storage 평가
    ↓
X299 / GPU / HPC 결정
    ↓
full 1 Ga production
    ↓
1001-frame QA
    ↓
web asset 생성
    ↓
EarthThruTime3D production integration
```

## 19. 첫 번째 핵심 milestone

전체 1 Ga 계산이 아니라 다음을 첫 milestone으로 한다.

> **원해상도 OPT1의 20 Ma 구간을 X299에서 재계산하고, 그 구간에서 1 Ma
> 간격의 mantle visualization output 21개를 생성하여 EarthThruTime3D에서
> 연속 재생한다.**

이 단계 하나로 다음을 판단할 수 있다.

-   CitcomS 재현 가능성
-   X299 실제 계산속도
-   RAM 요구량
-   1 Ma I/O 비용
-   공개 OPT1과의 일치도
-   1 Ma visualization의 가치
-   GPU/HPC 필요성

## 20. 최종 성공 기준

-   [ ] OPT1 input/code/data provenance 확보
-   [ ] reproducible CitcomS build
-   [ ] 공개 20 Ma OPT1과 재계산 결과 검증
-   [ ] 1 Ma output cadence 안정화
-   [ ] 1000--0 Ma, 1001-frame dataset 생성
-   [ ] frame별 metadata/provenance
-   [ ] EarthThruTime3D용 compressed assets
-   [ ] time slider에서 연속 mantle evolution 표현
-   [ ] 원 논문 결과와 재계산 결과의 차이 문서화

## Reference

Müller, R. D. et al. (2022). *A tectonic-rules-based mantle reference
frame since 1 billion years ago -- implications for supercontinent
cycles and plate--mantle system evolution*. Solid Earth, 13, 1127--1159.
DOI: 10.5194/se-13-1127-2022.
