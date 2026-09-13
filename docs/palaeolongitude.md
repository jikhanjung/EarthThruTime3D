# 고지자기 경도 고정 문제

판 모델과 고지리 지도를 같은 시각에서 겹쳐 보면, 오래된 시대로 갈수록 대륙 모양은
비슷한데 경도가 크게 어긋나는 일이 생긴다. 이 문서는 그 원인과 여러 연구 진영의 쟁점,
그리고 이 프로젝트에서 직접 잰 수치를 정리한다. 무엇이 자료이고 무엇이 가정인지를
구분하는 것이 목적이다.

## 요약

- 고지자기는 위도와 방향을 정하지만 경도는 정하지 못한다. 자전축 둘레의 회전은 자료에
  드러나지 않는다.
- 약 2억 년보다 젊은 시대는 해양 지각과 열점 흔적이 경도를 붙잡는다. 그보다 오래되면
  경도는 관측이 아니라 선택한 규칙이나 가설로 정해진다.
- Torsvik & Cocks(2017)는 2억 5천만~5억 5천만 년의 경도를, 대규모 화성암 지대와
  킴벌라이트가 맨틀 하부 거대 저속도 영역(LLSVP)의 가장자리 위에서 분출했다는 가정으로
  정했다. 이 가정이 성립하는지가 핵심 쟁점이다.
- 이 프로젝트의 측정에서 T&C는 255 Ma까지 Scotese 지도와 ±10° 안에서 맞고, 그 이전에는
  자전축 기준으로 최대 168°까지 벌어진다. Merdith(2021)는 같은 구간에서 ±22° 안에 머문다.
- T&C의 차이는 경도만이 아니다. 진극 이동 보정 층이 위도를 20~40° 옮긴다. 그 층을 빼면
  위도가 대부분 고지자기 값으로 돌아온다.

## 1. 왜 고지자기는 경도를 정하지 못하나

고지자기 해석은 지구 자기장을 자전축에 정렬된 쌍극자로 본다. 이 장은 자전축에 대해
대칭이므로, 암석에 남은 자화 방향은 그 땅덩이가 적도에서 얼마나 떨어져 있었는지와 어느
쪽을 향했는지는 알려주지만, 자전축 둘레 어느 경도에 있었는지는 알려주지 못한다.
위도선을 따라 움직인 판의 운동도 드러나지 않는다. 그래서 고지자기 기준틀을 쓰려면
경도를 따로 정하는 추가 정보가 필요하다. 흔한 방법은 기준 판 하나를 경도상 고정했다고
보는 것이다. [Apparent polar wander, Wikipedia][apw] 및
[Torsvik et al. 2012, Earth-Science Reviews][torsvik2012]가 이 점을 설명한다.

## 2. 경도를 정하는 방법들

### 해양 지각과 판 회로

해저 자기 이상과 단열대로 판끼리의 상대 운동을 복원할 수 있다. 하지만 가장 오래된
해양 지각이 약 2억 년이므로 이 방법이 닿는 범위도 그만큼이다.

### 열점 기준틀

열점이 맨틀에 대해 거의 고정돼 있다고 보고 열점 흔적으로 판의 절대 운동을 정한다.
열점이 조금씩 움직인다고 보는 이동 열점 기준틀도 있다. 추적 가능한 열점 흔적은 대략
1억 2천만~1억 3천만 년까지다. T&C 회전 파일도 전 지구 이동 열점 기준틀(GMHRF)을
1억 2천만 년까지만 쓴다고 적었다.

### 판 경계 기원 영역(Plume Generation Zone) 방법

맨틀 바닥의 두 거대 저속도 영역이 수억 년 동안 제자리에 있었고, 대규모 화성암 지대와
킴벌라이트가 그 가장자리에서 솟은 플룸으로 분출했다고 가정한다. 그러면 옛 분출 자리를
오늘날 가장자리 위에 올리는 회전으로 경도를 정할 수 있다.

- [Burke & Torsvik 2004][burke2004]: 지난 2억 년의 대규모 화성암 지대를 고지자기로 되돌리면
  맨틀 하부 저속도 영역 부근에 모인다고 보였다.
- [Torsvik et al. 2006][torsvik2006]: 그 분출이 저속도 영역의 가장자리에서 생긴다고 보았다.
- [Burke et al. 2008][burke2008]: 이 가장자리를 "판 경계 기원 영역"이라 불렀다.
- [Torsvik et al. 2010][torsvik2010]: 현생누대 킴벌라이트 대부분이 같은 가장자리에서
  분출했다고 보고, 그 구조가 적어도 2억 년, 어쩌면 5억 4천만 년 안정했다고 추정했다.
- [Torsvik et al. 2014][torsvik2014]: 판게아 형성 이후의 상관을 판게아 이전으로 확장하는
  재구성 방법을 제시하고, 진극 이동을 보정한 고지자기 기준틀로 초기 고생대까지의
  절대 운동 모델을 만들었다.

### 섭입 슬랩 잔존물 기준틀

[van der Meer et al. 2010][vandermeer2010]은 하부 맨틀 단층 영상에서 섭입된 판의 잔재
28곳을 찾아 조산대와 연결하고, 3억 년 전까지 섭입대의 경도가 기존 재구성과 최대 18°
어긋난다고 보고했다. 이 방향에서 섭입 기준틀이라는 계열이 나왔다.

### 구조 규칙에 따른 최적화 맨틀 기준틀

[Tetley et al. 2019][tetley2019]는 열점 흔적, 순 암석권 회전의 상한, 해구 이동 속도를 함께
맞추는 최적화로 2억 2천만 년 이후의 절대 기준틀을 만들었다.
[Müller et al. 2022][muller2022]는 이런 구조 규칙 기반 최적화를 10억 년까지 확장했다.

### 최소 대륙 이동 기준틀

[Wagenaar et al. 2025][wagenaar2025]는 대륙의 절대 이동 총량을 최소로 두는 규칙으로
약 3억 5천만 년까지 판 운동을 복원했다.

### 고지자기 기준틀 그대로 두기

경도를 물리적으로 붙잡지 않고 고지자기 기준틀에 관례만 더하는 방법이다. Merdith et al.
(2021) 자료의 readme는 이 모델이 "purely palaeomagnetic reference frame"에 있다고 적는다.
Müller et al.(2022) readme는 기후와 관련된 분석에는 고지자기 기준틀을 쓰라고 권한다.
[Jones & Domeier 2024][jones2024]는 다섯 판 모델(Wright 2013, Matthews 2016, Torsvik & Cocks 2016,
Scotese 2016, Merdith 2021)의 고(古)위도를 1백만 년 간격 격자로 계산한 자료를 고지자기 기준틀에서 만들어 공개했다. 위도가 필요한
분석에는 경도 가설이 섞이지 않은 기준틀을 쓴다는 같은 판단이다.

## 3. 쟁점

### 3.1 거대 저속도 영역은 정말 고정돼 있었나

판 경계 기원 영역 방법의 전제다. 반론이 이어지고 있다.

- [Conrad, Steinberger & Torsvik 2013][conrad2013]은 2억 5천만 년 동안 판 운동의 사중극 성분이
  제자리에 머물렀다며 두 저속도 영역도 그동안 고정돼 있었다고 주장했다.
  [Rudolph & Zhong 2013][quadrupole-comment]은 사중극의 안정이 곧 저속도 영역의 고정을 뜻한다는
  추론에 근거가 부족하다고 반박했고, 저자들이 [답신][quadrupole-reply]을 냈다.
- [Flament et al. 2017][flament2017]은 유라시아 밑의 작은 저속도 구조(Perm 이상체)를 두고,
  고정된 두 영역의 가장자리에서만 플룸이 솟는다는 그림에 의문을 제기했다.
- [Davaille & Romanowicz 2020][davaille2020]은 저속도 영역이 두꺼운 정체 더미가 아니라 열화학
  플룸의 다발일 수 있다고 보았다.
- [Cucchiaro et al. 2025][cucchiaro2025]는 여러 분출 목록, 단층 영상 모델, 맨틀 흐름 모델을
  통계적으로 비교해, 대규모 분출 대부분이 움직이는 기저 맨틀 구조 위에서 기원했다고 보고했다.

### 3.2 분출 자리와 가장자리의 상관은 통계적으로 유의한가

- [Austermann et al. 2014][austermann2014]는 몬테카를로 검정으로, 같은 상관이 가장자리가 아니라
  저속도 영역 전체, 또는 평균보다 느린 하부 맨틀 영역 전체에 무작위로 생긴 플룸으로도 똑같이,
  혹은 더 잘 설명된다고 보았다.
- [Davies, Goes & Sambridge 2015][davies2015]는 아프리카 영역에서는 상관이 강하지만 길쭉한
  형태 탓이 크고, 태평양 영역에서는 약하며, 분포가 영역 전체에 고르게 퍼진 것과도 모순되지
  않는다고 보았다.
- [Doubrovine et al. 2016][doubrovine2016]은 경험적 분포 함수 통계로 다시 검정해 상관을
  기각하지 못한다고 답했다.

### 3.3 판게아 이전에는 독립적으로 검증하기 어렵다

판게아 이후에는 열점과 해양 지각이 경도를 따로 붙잡으므로 분출 자리와 가장자리의 상관을
독립적으로 확인할 수 있다. 그 이전에는 경도 자체를 그 상관으로 정하므로, 같은 자료로
가정을 검증하기가 어렵다. Torsvik et al.(2014)은 이를 판게아 이전에도 상관이 유지되는지
시험하는 방법으로 제시했다. 이 절의 문제 제기는 이 프로젝트의 정리이며 특정 논문의
주장을 옮긴 것이 아니다.

### 3.4 진극 이동 보정은 경도 고정과 별개의 가설이다

[Steinberger & Torsvik 2008][steinberger2008]은 고지자기 기준틀에서 대륙 전체의 평균 이동과
회전을 계산해, 특정 시기의 전체 회전을 진극 이동으로 해석했다. 이 보정은 적도 위 축 둘레
회전이라 경도뿐 아니라 위도도 옮긴다. 경도 고정 가설을 받아들인다고 해서 진극 이동 보정까지
받아들여야 하는 것은 아니다. 위도는 기후대를 뜻하므로 이 구분이 중요하다.

## 4. Torsvik & Cocks 회전 파일이 스스로 밝히는 규칙

회전 파일 첫 줄들, 판 001의 주석이다.

```
001  0.0 ... ! PM-HYBRID (PID=1) is a PM frame with longitudes adjusted to match
001 10.0 ... ! 1) TPW observed in GMHFR for the last 120 Ma,
001 20.0 ... ! 2) LIPs and kimberlites for 250-550 Ma, and
001 30.0 ... ! 3) a smooth transition imposed between 120 and 250 Ma
001 40.0 ... ! DATE 14 SEPTEMBER 2012
001 50.0 ... ! Super duper HYBRID (PID=0) is the GMHRF for ages <= 120 Ma,
001 60.0 ... ! and PM-HYBRID corrected for TPW for 120-550 Ma
```

두 층이다. 판 1번 `PM-HYBRID`는 고지자기 기준틀에 경도만 맞춘 것이다. 최근 1억 2천만 년은
이동 열점 기준틀의 진극 이동에, 2억 5천만~5억 5천만 년은 화성암 지대와 킴벌라이트에 맞추고,
그 사이는 매끄럽게 이었다. 판 0번은 모든 판이 매달리는 뿌리로, 1억 2천만 년까지는 이동 열점
기준틀이고 그 이전은 판 1번에 진극 이동 보정을 더했다. 판 001 줄의 극 대부분이 위도 0°,
경도 11°에 놓인 것이 그 보정 회전이다. 둘째 줄의 `GMHFR`은 원문 오타로 `GMHRF`를 뜻한다.

## 5. 이 프로젝트에서 잰 것

모든 수치는 다음 명령으로 재현된다. 판 모델 묶음과 분할 결과가 필요하다.

```bash
.venv/bin/python scripts/measure_longitude_offsets.py all
```

### 5.1 Scotese 지도에 가장 잘 맞는 자전축 회전

모델의 육지를 360 × 180 정거원통 격자에 그리고, 가로로 1°씩 굴려 가며 Scotese 지도에서 분할한
육지와 겹침이 최대가 되는 각도를 찾았다. 자전축 둘레 회전은 정거원통 격자에서 정확히 가로
이동이다. 겹침은 면적 가중 교집합 나누기 합집합이다.

| 시대 | T&C 최적 회전 | 겹침 | Merdith 최적 회전 | 겹침 |
|---|---|---|---|---|
| 0 Ma | +1° | 0.78 | +1° | 0.60 |
| 152 Ma | −7° | 0.59 | −22° | 0.59 |
| 255 Ma | +3° | 0.61 | +1° | 0.62 |
| 306 Ma | +27° | 0.38 | +3° | 0.39 |
| 356 Ma | +73° | 0.33 | −21° | 0.31 |
| 390 Ma | +95° | 0.36 | +11° | 0.35 |
| 425 Ma | +133° | 0.31 | +12° | 0.34 |
| 458 Ma | +118° | 0.25 | −7° | 0.38 |
| 514 Ma | +168° | 0.26 | +22° | 0.30 |

T&C는 255 Ma까지 Scotese와 맞다가 306 Ma부터 벌어진다. 회전 파일이 밝힌 규칙 전환 시점과
일치한다. Merdith는 고생대 내내 Scotese와 가깝다. 즉 고생대 경도에서 예외는 T&C 쪽이다.

### 5.2 같은 지점, 두 모델의 차이

T&C에서 Merdith를 뺀 값이다.

| 시대 | 판 | 경도 차 | 위도 차 |
|---|---|---|---|
| 255 Ma | 아프리카 | −1.2° | +1.5° |
| 306 Ma | 아프리카 | −24.6° | −4.3° |
| 356 Ma | 아프리카 | −39.6° | +11.1° |
| 425 Ma | 아프리카 | −112.1° | +18.2° |
| 425 Ma | 발티카 | −45.6° | +30.5° |
| 514 Ma | 아프리카 | +159.4° | +28.8° |
| 514 Ma | 발티카 | −59.8° | +40.5° |

위도가 함께 움직이고, 같은 시대에도 지점마다 경도 차가 다르다. 자전축 둘레의 순수한 경도
회전이라면 위도는 그대로여야 한다. 따라서 차이는 일반적인 3차원 회전이고, 경도만 맞춰서는
해소되지 않는다.

### 5.3 진극 이동 보정 층을 빼면

T&C 위도에서 Merdith 위도를 뺀 값을, 판 0번과 판 1번 기준으로 비교했다.

| 시대 | 판 | 판 0번 층 | 판 1번 층 |
|---|---|---|---|
| 306 Ma | 발티카 | −8.0° | −7.4° |
| 356 Ma | 남아메리카 | +18.8° | −2.6° |
| 356 Ma | 북아메리카 | +12.3° | −8.5° |
| 356 Ma | 발티카 | +14.0° | −5.3° |
| 425 Ma | 발티카 | +30.5° | −0.5° |
| 425 Ma | 북아메리카 | +12.2° | −1.0° |
| 514 Ma | 아프리카 | +28.8° | +2.1° |
| 514 Ma | 발티카 | +40.5° | +1.5° |
| 425 Ma | 아프리카 | +18.2° | +12.7° |
| 425 Ma | 남아메리카 | +19.3° | −13.5° |

판 1번 층에서는 20~40°였던 위도 차이가 대체로 10° 안으로 줄어든다. 425 Ma 아프리카와
남아메리카처럼 10° 넘게 남는 곳도 있다. 남는 차이는 두 모델의 극 자료 편집이 다른 데서 오는
것으로 추정되며, 이 프로젝트가 확인한 것은 아니다. 판 1번 층은 고지자기 위도를 유지하면서 경도만
화성암 지대 가정으로 고정한 기준틀로 읽을 수 있다.

### 5.4 측정의 한계

- 300 Ma 이전에는 최적 회전의 겹침이 0.25~0.40으로 젊은 시대의 0.55~0.78보다 낮다. 경도만으로
  맞지 않는다는 뜻이기도 하지만, 옛 Scotese 지도의 분할이 어두운 중심부만 잡는 약점(devlog 003)도
  섞여 있다.
- 판 1번 층을 Scotese에 맞춘 최적 회전은 356~514 Ma에서 +17°, −170°, +82°, +44°, +129°로 널뛴다.
  겹침은 458 Ma에서 0.25 → 0.32, 514 Ma에서 0.26 → 0.38로 판 0번 층보다 오히려 낫다.
  겹침이 낮아 최적값이 잘 정해지지 않는 구간이다. 이 구간의 근거로는 5.2와 5.3의 모델 간 비교가
  더 단단하다.
- 지점 비교는 판마다 한 점씩이다. 판 전체의 회전 차이를 요약한 값이 아니다.

## 6. 자료별 경도 규칙

| 자료 | 경도를 정한 방식 | 근거 |
|---|---|---|
| Scotese 웹 지도(© 2002) | 가진 자료에 규칙이 적혀 있지 않다. 판 경계 기원 영역 방법보다 앞선다. | 지도 표기, [PALEOMAP PaleoAtlas 2016][scotese2016] |
| Merdith et al. 2021 | 순수 고지자기 기준틀 | 모델 readme |
| Müller et al. 2022 | 구조 규칙 최적화 맨틀 기준틀. 고지자기 기준틀 파일도 함께 제공 | 모델 readme, [Müller et al. 2022][muller2022] |
| Cao et al. 2024 | 0~650 Ma 회전 수열이 Merdith와 96% 바이트 일치 | 이 프로젝트 측정(`sources/plate-models/cao2024.json`) |
| Matthews et al. 2016 | 혼합 맨틀 기준틀(GK07). 세부는 원 논문 | 회전 파일명, 목록 파일 |
| Torsvik & Cocks 2017 | 판 1번: 고지자기 + 경도 맞춤. 판 0번: 여기에 진극 이동 보정 | 회전 파일 머리말 |

## 7. 이 프로젝트에서의 선택지

비교가 목적인 뷰어이므로 기준틀 선택은 해석이고, 한 가지를 조용히 기본값으로 박지 않는다.

- **원래대로.** 각 모델을 출판된 기준틀 그대로 보인다. 기본값.
- **기준 판 맞춤.** 시대마다 각 모델을 회전시켜, 그 모델의 아프리카가 기준 모델의 아프리카
  자리에 오게 한다. 회전 모델끼리 정확히 계산되고 분할 품질에 좌우되지 않는다. 기준틀 차이가
  한꺼번에 사라지고, 남는 어긋남은 대륙 상대 배치에 대한 모델 간 불일치다.
- **자전축 회전만 맞춤.** 고지자기가 비워 둔 자유도만 건드려 위도를 보존한다. 5.2처럼 위도까지
  다른 경우에는 부족하다.
- **Scotese 지도에 맞춤.** 바탕 지도와 겹쳐 보기에는 좋지만 Scotese를 임의로 기준 삼는 것이고,
  옛 지도에서는 분할 품질에 결과가 좌우된다.

기준 판 맞춤을 한다면 기준으로 T&C 판 1번 층이 가장 설득력 있어 보인다. 경도는 물리적 가정으로
고정하고 위도는 측정값을 쓰기 때문이다. 다만 세 가지 제약이 따른다.

- 판 경계 기원 영역 가정은 3.1~3.3의 쟁점을 안고 있다.
- T&C는 540 Ma까지만 닿는다. 지도는 650 Ma, Cao는 1800 Ma까지 가므로 그 너머는 원래대로 두어야
  한다.
- T&C 자료에는 이용 조건이 없다. 이를 기준으로 정렬한 다른 모델의 화면도 T&C 회전에서 계산되므로,
  이 기준틀은 T&C와 같이 접근 키 뒤에 두는 것이 일관된다.

## 출처

- Apparent polar wander. Wikipedia. <https://en.wikipedia.org/wiki/Apparent_polar_wander>
- Torsvik, T. H., et al., 2012. Phanerozoic polar wander, palaeogeography and dynamics. Earth-Science Reviews, 114. <https://www.sciencedirect.com/science/article/abs/pii/S0012825212000797>
- Burke, K., and Torsvik, T. H., 2004. Derivation of Large Igneous Provinces of the past 200 million years from long-term heterogeneities in the deep mantle. Earth and Planetary Science Letters, 227, 531–538. <https://doi.org/10.1016/j.epsl.2004.09.015>
- Torsvik, T. H., Smethurst, M. A., Burke, K., and Steinberger, B., 2006. Large igneous provinces generated from the margins of the large low-velocity provinces in the deep mantle. Geophysical Journal International, 167, 1447–1460. <https://doi.org/10.1111/j.1365-246X.2006.03158.x>
- Burke, K., Steinberger, B., Torsvik, T. H., and Smethurst, M. A., 2008. Plume Generation Zones at the margins of Large Low Shear Velocity Provinces on the core–mantle boundary. Earth and Planetary Science Letters, 265. <https://www.sciencedirect.com/science/article/abs/pii/S0012821X07006036>
- Torsvik, T. H., Burke, K., Steinberger, B., Webb, S. J., and Ashwal, L. D., 2010. Diamonds sampled by plumes from the core–mantle boundary. Nature, 466, 352–355. <https://www.nature.com/articles/nature09216>
- Torsvik, T. H., van der Voo, R., Doubrovine, P. V., Burke, K., Steinberger, B., et al., 2014. Deep mantle structure as a reference frame for movements in and on the Earth. PNAS, 111. <https://doi.org/10.1073/pnas.1318135111>
- Steinberger, B., and Torsvik, T. H., 2008. Absolute plate motions and true polar wander in the absence of hotspot tracks. Nature, 452, 620–623. <https://www.nature.com/articles/nature06824>
- van der Meer, D. G., Spakman, W., van Hinsbergen, D. J. J., Amaru, M. L., and Torsvik, T. H., 2010. Towards absolute plate motions constrained by lower-mantle slab remnants. Nature Geoscience, 3, 36–40. <https://doi.org/10.1038/ngeo708>
- Tetley, M. G., Williams, S. E., Gurnis, M., Flament, N., and Müller, R. D., 2019. Constraining absolute plate motions since the Triassic. Journal of Geophysical Research: Solid Earth, 124. <https://doi.org/10.1029/2019JB017442>
- Müller, R. D., et al., 2022. A tectonic-rules-based mantle reference frame since 1 billion years ago – implications for supercontinent cycles and plate–mantle system evolution. Solid Earth, 13, 1127–1159. <https://se.copernicus.org/articles/13/1127/2022/>
- Wagenaar, S., Vaes, B., and van Hinsbergen, D. J. J., 2025. Journal of Geophysical Research: Solid Earth (minimum-continent-motion reference frame). <https://doi.org/10.1029/2024JB030430>
- Jones, L. A., and Domeier, M., 2024. A Phanerozoic gridded dataset for palaeogeographic reconstructions. Scientific Data, 11, 710. <https://doi.org/10.1038/s41597-024-03468-w>
- Conrad, C. P., Steinberger, B., and Torsvik, T. H., 2013. Stability of active mantle upwelling revealed by net characteristics of plate tectonics. Nature, 498, 479–482. <https://pubmed.ncbi.nlm.nih.gov/23803848/>
- Rudolph, M. L., and Zhong, S., 2013. Does quadrupole stability imply LLSVP fixity? Nature, 503, E3–E4. <https://www.nature.com/articles/nature12792>
- Conrad, C. P., Steinberger, B., and Torsvik, T. H., 2013. Conrad et al. reply. Nature, 503. <https://www.nature.com/articles/nature12793>
- Flament, N., Williams, S., Müller, R. D., Gurnis, M., and Bower, D. J., 2017. Origin and evolution of the deep thermochemical structure beneath Eurasia. Nature Communications, 8, 14164. <https://www.nature.com/articles/ncomms14164>
- Davaille, A., and Romanowicz, B., 2020. Deflating the LLSVPs: Bundles of mantle thermochemical plumes rather than thick stagnant “piles”. Tectonics, 39. <https://doi.org/10.1029/2020TC006265>
- Cucchiaro, A., Flament, N., Arnould, M., et al., 2025. Communications Earth & Environment (large eruptions sourced above mobile basal mantle structures). <https://www.nature.com/articles/s43247-025-02482-z>
- Austermann, J., Kaye, B. T., Mitrovica, J. X., and Huybers, P., 2014. A statistical analysis of the correlation between large igneous provinces and lower mantle seismic structure. Geophysical Journal International, 197, 1–9. <https://academic.oup.com/gji/article/197/1/1/683265>
- Davies, D. R., Goes, S., and Sambridge, M., 2015. On the relationship between volcanic hotspot locations, the reconstructed eruption sites of large igneous provinces and deep mantle seismic structure. Earth and Planetary Science Letters, 411. <https://www.sciencedirect.com/science/article/abs/pii/S0012821X14007523>
- Doubrovine, P. V., Steinberger, B., and Torsvik, T. H., 2016. A failure to reject: Testing the correlation between large igneous provinces and deep mantle structures with EDF statistics. Geochemistry, Geophysics, Geosystems, 17. <https://doi.org/10.1002/2015GC006044>
- Scotese, C. R., 2016. PALEOMAP PaleoAtlas for GPlates and the PaleoData Plotter Program. PALEOMAP Project; GSA North-Central Section abstract. <https://gsa.confex.com/gsa/2016NC/webprogram/Paper275387.html>
- Torsvik & Cocks 2017, *Earth History and Palaeogeography*, Cambridge University Press. 회전 파일 머리말은 CEED6 묶음에서 읽었다. 목록 파일 `sources/plate-models/torsvikcocks2017.json`.
- Merdith et al. 2021, Müller et al. 2022 모델 readme. 목록 파일 `sources/plate-models/`.

[apw]: https://en.wikipedia.org/wiki/Apparent_polar_wander
[torsvik2012]: https://www.sciencedirect.com/science/article/abs/pii/S0012825212000797
[burke2004]: https://doi.org/10.1016/j.epsl.2004.09.015
[torsvik2006]: https://doi.org/10.1111/j.1365-246X.2006.03158.x
[burke2008]: https://www.sciencedirect.com/science/article/abs/pii/S0012821X07006036
[torsvik2010]: https://www.nature.com/articles/nature09216
[torsvik2014]: https://doi.org/10.1073/pnas.1318135111
[steinberger2008]: https://www.nature.com/articles/nature06824
[vandermeer2010]: https://doi.org/10.1038/ngeo708
[tetley2019]: https://doi.org/10.1029/2019JB017442
[muller2022]: https://se.copernicus.org/articles/13/1127/2022/
[wagenaar2025]: https://doi.org/10.1029/2024JB030430
[jones2024]: https://doi.org/10.1038/s41597-024-03468-w
[conrad2013]: https://pubmed.ncbi.nlm.nih.gov/23803848/
[quadrupole-comment]: https://www.nature.com/articles/nature12792
[quadrupole-reply]: https://www.nature.com/articles/nature12793
[flament2017]: https://www.nature.com/articles/ncomms14164
[davaille2020]: https://doi.org/10.1029/2020TC006265
[cucchiaro2025]: https://www.nature.com/articles/s43247-025-02482-z
[austermann2014]: https://academic.oup.com/gji/article/197/1/1/683265
[davies2015]: https://www.sciencedirect.com/science/article/abs/pii/S0012821X14007523
[doubrovine2016]: https://doi.org/10.1002/2015GC006044
[scotese2016]: https://gsa.confex.com/gsa/2016NC/webprogram/Paper275387.html
