// Preview: where deep water formed at each FOAM slice, from the literature (collected and
// Crossref-checked 2026-09-26; condensed in the session's deepwater_literature.md). Only
// regions the sources support go on the map: "consensus" (several independent lines of
// evidence, no strong dissent) and "likely" (supported, with caveats). Debated regions are
// named in the note with both sides, not drawn. Each marker is anchored on a present-day
// continental margin and carried to the shown age by the pin rotation, so its place is the
// region's, not an exact site. "warm": warm, salty water sinking at low latitude.
export const DEEPWATER = {
  0: {
    marks: [
      { level: 'consensus', at: [-45, -77], name: '웨들해' },
      { level: 'consensus', at: [168, -77], name: '로스해' },
      { level: 'consensus', at: [140, -67.5], name: '아델리 해안' },
      { level: 'consensus', at: [70, -69], name: '다언리곶' },
      { level: 'consensus', at: [-25, 71], name: '노르딕해' },
      { level: 'consensus', at: [-45, 61], name: '북대서양 아한대' },
    ],
    note: '남극 둘레(웨들해·로스해·아델리 해안·다언리곶)의 남극 저층수와 노르딕해·북대서양 아한대의 북대서양 심층수 (Orsi 1999; Ohshima 2013; Dickson 1994). 북태평양과 인도양에서는 깊은 물이 생기지 않는다 (Ferreira 2018). 논쟁: 래브라도해의 비중 (Lozier 2019).',
  },
  20: {
    marks: [
      { level: 'consensus', at: [-45, -77], name: '남극해 (웨들해 쪽)' },
      { level: 'likely', at: [-25, 71], name: '북대서양·노르딕해' },
    ],
    note: '남극해가 주된 원천 (Woodruff 1989; Wright 1992; Herold 2012). 북대서양에서도 깊은 물이 생겼을 가능성이 크다 (Scher 2008; Thomas 2007). 논쟁: 북대서양 심층수의 세기 (약함: Woodruff 1989, Poore 2006 / 강함: 퇴적 드리프트와 εNd 자료), 북태평양 (McKinley 2019), 테티스의 따뜻하고 짠 물 (Hamon 2013 / Bialik 2019).',
  },
  40: {
    marks: [
      { level: 'consensus', at: [140, -67.5], name: '남극해 (대표 지점)' },
    ],
    note: '남극해가 주된 원천이라는 데 이견이 없다. 태평양 쪽(아델리 해안)은 가능성이 큰 위치 (Huck 2017; Thomas 2014; Borrelli 2014; Hutchinson 2021). 논쟁: 북태평양 (Thomas 2014, McKinley 2019 / Thomas 2004, Hague 2012), 북대서양의 간헐적 심층수 (Hohbein 2012, Vahlenkamp 2018 / Stoker 2013, Coxall 2018).',
  },
  60: {
    marks: [
      { level: 'consensus', at: [0, -71], name: '남극해' },
      { level: 'likely', at: [150, 59.5], name: '북태평양' },
    ],
    note: '남극해에서 생긴 물이 대서양과 인도양 깊은 곳을 채웠다 (Thomas 2003; Batenburg 2018). 북태평양도 가능성이 크나 주로 한 연구진의 εNd 자료에 기댄다 (Thomas 2004; Hague 2012). 논쟁: 북대서양 (MacLeod 2011 / Thomas 2003, Batenburg 2018), 저위도의 따뜻하고 짠 물.',
  },
  80: {
    marks: [
      { level: 'consensus', at: [0, -71], name: '남쪽 고위도 (대서양 쪽)' },
      { level: 'consensus', at: [70, -69], name: '남쪽 고위도 (인도양 쪽)' },
      { level: 'likely', at: [150, 59.5], name: '북태평양' },
    ],
    note: '남쪽 고위도(남대서양·인도양 쪽)에 원천이 있었다 (Robinson 2010; Murphy 2012; Moiroud 2016; Donnadieu 2016). 북태평양은 가능성이 크나 자료가 적다 (Hague 2012; Donnadieu 2016). 논쟁: 남쪽 원천이 어느 해역이었는지 (Donnadieu 2016 / Ladant 2020), 남쪽 물이 이미 북대서양까지 갔는지 (Robinson 2012, Murphy 2013 / Voigt 2013), 따뜻하고 짠 물 (Brass 1982; Friedrich 2012).',
  },
  100: {
    marks: [
      { level: 'likely', at: [70, -69], name: '남쪽 고위도 (인도양 쪽)' },
      { level: 'likely', at: [-130, -75], name: '남태평양 쪽' },
      { level: 'likely', at: [150, 59.5], name: '북태평양 (모형만)' },
      { level: 'likely', warm: true, at: [-17, 21], name: '막힌 원시 북대서양의 따뜻하고 짠 물' },
    ],
    note: '남쪽 고위도(인도양 쪽, 남태평양)에서 깊은 물이 생겼을 가능성이 크다 (Murphy 2012; Poulsen 2001; Donnadieu 2016). 북태평양은 모형 결과뿐이다 (Donnadieu 2016). 막혀 있던 원시 북대서양은 저위도·테티스에서 온 20–25 °C의 따뜻하고 짠 물로 찼다 (Friedrich 2008; Martin 2012; Liu 2023). 논쟁: 따뜻하고 짠 물이 전 지구의 주된 방식이었는지 (Brass 1982 / Murphy 2012).',
  },
};

// The overturning state in the time windows, one entry per interval (young <= ka < old),
// from the literature (data/sources/currents-preview/lit/amoc_intervals.json: Greenland
// stadials and interstadials after Rasmussen 2014, doi:10.1016/j.quascirev.2014.09.007;
// Heinrich stadials after Guillevic 2014, doi:10.5194/cp-10-2115-2014; modes after
// Rahmstorf 2002, doi:10.1038/nature01090). Events under 500 years are merged into a
// neighbour; variant names the belt drawn (conveyor.json).
export const QUATERNARY = [
  { young: 0, old: 7.0, mode: 'warm', variant: 'present', name: "Holocene (mid-late; Labrador + Nordic sinks)", name_ko: "홀로세 중·후기", confidence: 'consensus', note: "북대서양 깊은 곳의 Pa/Th가 약 1만 1천 년 동안 거의 변하지 않았고 (Lippold 2019), 래브라도해의 깊은 물은 약 7천 년 전에 자리 잡았다 (Hillaire-Marcel 2001). (여러 증거가 일치)", refs: ["10.1029/2019GL084988", "10.1038/35074059", "10.1029/2011PA002155"] },
  { young: 7.0, old: 11.703, mode: 'warm', variant: 'nolab', name: "Early Holocene (Nordic sink only; 8.2, 9.3, 11.4 ka events merged)", name_ko: "홀로세 초기", confidence: 'likely', note: "깊은 순환은 오늘과 비슷했으나 (Lippold 2019), 래브라도해에서는 아직 깊은 물이 생기지 않았다 (Hillaire-Marcel 2001; Thornalley 2010). 그래서 래브라도해의 가라앉는 곳은 뺐다. (뒷받침되나 단서가 있음)", refs: ["10.1029/2019GL084988", "10.1038/35074059", "10.1029/2009PA001833", "10.1126/science.1127213"] },
  { young: 11.703, old: 12.896, mode: 'weak', variant: 'weak', name: "Younger Dryas / GS-1", name_ko: "영거 드라이아스 (GS-1)", confidence: 'likely', note: "북대서양의 뒤집힘이 약해졌다 (McManus 2004; Lynch-Stieglitz 2017). 논쟁: 거의 줄지 않았다는 결과도 있다 (Gherardi 2009). (뒷받침되나 단서가 있음)", refs: ["10.1038/nature02494", "10.1146/annurev-marine-010816-060415", "10.1038/s41561-023-01140-3", "10.1029/2008PA001696"] },
  { young: 12.896, old: 14.692, mode: 'warm', variant: 'nolab', name: "GI-1 Boelling-Alleroed (GI-1a-e merged)", name_ko: "뵐링-알레뢰드 (GI-1)", confidence: 'likely', note: "뒤집힘이 빠르게 되살아났다 (McManus 2004). (뒷받침되나 단서가 있음)", refs: ["10.1038/nature02494", "10.1038/nature01090", "10.1029/2008PA001696"] },
  { young: 14.692, old: 17.48, mode: 'weak', variant: 'weak', name: "HS1 (GS-2.1a)", name_ko: "하인리히 아빙기 1 (HS1)", confidence: 'likely', note: "뒤집힘이 거의 멈췄다는 결과 (McManus 2004)와, 약해졌지만 깊은 물이 계속 생겼다는 결과 (Gherardi 2009; Repschläger 2021)가 맞선다. (뒷받침되나 단서가 있음)", refs: ["10.1038/nature02494", "10.1029/2008PA001696", "10.1038/s41561-023-01140-3", "10.1016/j.quascirev.2021.107145", "10.1016/j.quascirev.2014.09.007"] },
  { young: 17.48, old: 23.34, mode: 'cold', variant: 'cold', name: "LGM (GS-2.1b-c; GI-2.1, GS-2.2, GI-2.2 merged)", name_ko: "최종 빙기 극대기", confidence: 'likely', note: "북쪽에서 가라앉은 물은 약 1.5 km 깊이에 머물고, 남쪽에서 온 물이 약 2 km 아래를 채웠다 (Curry & Oppo 2005; Lynch-Stieglitz 2007). 가라앉는 곳은 아이슬란드 남쪽으로 옮겨 갔다 (Sarnthein 1994). 논쟁: 세기는 오늘만큼 강했다 (Lippold 2012) / 얕고 약했다 (Pöppelmeier 2023). 노르딕해에서도 물이 계속 가라앉았다는 결과도 있다 (Crocket 2011). (뒷받침되나 단서가 있음)", refs: ["10.1029/2004PA001021", "10.1126/science.1137127", "10.1126/science.259.5098.1148", "10.1029/93PA03301", "10.1038/nature14059", "10.1126/science.1172873"] },
  { young: 23.34, old: 24.43, mode: 'weak', variant: 'weak', name: "HS2 (late GS-3)", name_ko: "하인리히 아빙기 2 (HS2)", confidence: 'likely', note: "하인리히 아빙기 2 (Dong 2022): 뒤집힘이 크게 약했다 (Henry 2016). (뒷받침되나 단서가 있음)", refs: ["10.1038/s41467-022-33583-4", "10.5194/cp-10-2115-2014", "10.1126/science.aaf5529", "10.1016/j.quascirev.2014.09.007"] },
  { young: 24.43, old: 27.78, mode: 'cold', variant: 'cold', name: "GS-3 before HS2 (GI-3 merged)", name_ko: "그린란드 아빙기 GS-3", confidence: 'likely', note: "버뮤다 해팽의 Pa/Th가 아빙기마다 높아지고 δ13C가 낮아져, 뒤집힘이 약하고 얕았다 (Henry 2016). (뒷받침되나 단서가 있음)", refs: ["10.1126/science.aaf5529", "10.1016/j.quascirev.2014.09.007", "10.1038/nature01090"] },
  { young: 27.78, old: 28.9, mode: 'cold', variant: 'cold', name: "GS-4 (GI-4 merged)", name_ko: "그린란드 아빙기 GS-4", confidence: 'likely', note: "버뮤다 해팽의 Pa/Th가 아빙기마다 높아지고 δ13C가 낮아져, 뒤집힘이 약하고 얕았다 (Henry 2016). (뒷받침되나 단서가 있음)", refs: ["10.1126/science.aaf5529", "10.1016/j.quascirev.2014.09.007"] },
  { young: 28.9, old: 30.6, mode: 'cold', variant: 'cold', name: "GS-5.1 (HS3, muted)", name_ko: "그린란드 아빙기 GS-5.1 · HS3", confidence: 'debated', note: "하인리히 사건 3의 영향은 약해서 (Henry 2016) 추운 상태로 두었다. (논쟁 중)", refs: ["10.1126/science.aaf5529", "10.5194/cp-10-2115-2014", "10.1016/j.quascirev.2014.09.007"] },
  { young: 30.6, old: 32.5, mode: 'cold', variant: 'cold', name: "GS-5.2 (GI-5.1, GI-5.2 merged)", name_ko: "그린란드 아빙기 GS-5.2", confidence: 'likely', note: "버뮤다 해팽의 Pa/Th가 아빙기마다 높아지고 δ13C가 낮아져, 뒤집힘이 약하고 얕았다 (Henry 2016). (뒷받침되나 단서가 있음)", refs: ["10.1126/science.aaf5529", "10.1016/j.quascirev.2014.09.007"] },
  { young: 32.5, old: 33.74, mode: 'cold', variant: 'cold', name: "GS-6 (GI-6 merged)", name_ko: "그린란드 아빙기 GS-6", confidence: 'likely', note: "버뮤다 해팽의 Pa/Th가 아빙기마다 높아지고 δ13C가 낮아져, 뒤집힘이 약하고 얕았다 (Henry 2016). (뒷받침되나 단서가 있음)", refs: ["10.1126/science.aaf5529", "10.1016/j.quascirev.2014.09.007"] },
  { young: 33.74, old: 34.74, mode: 'cold', variant: 'cold', name: "GS-7", name_ko: "그린란드 아빙기 GS-7", confidence: 'likely', note: "버뮤다 해팽의 Pa/Th가 아빙기마다 높아지고 δ13C가 낮아져, 뒤집힘이 약하고 얕았다 (Henry 2016). (뒷받침되나 단서가 있음)", refs: ["10.1126/science.aaf5529", "10.1016/j.quascirev.2014.09.007"] },
  { young: 34.74, old: 35.48, mode: 'warm', variant: 'nolab', name: "GI-7 (a-c)", name_ko: "그린란드 아간빙기 GI-7", confidence: 'likely', note: "Pa/Th와 δ13C가 오늘에 가까워 뒤집힘이 깊었고 (Henry 2016), 노르딕해에서 먼 바다 대류가 있었다 (Dokken & Jansen 1999). (뒷받침되나 단서가 있음)", refs: ["10.1126/science.aaf5529", "10.1038/46753", "10.1016/j.quascirev.2014.09.007"] },
  { young: 35.48, old: 36.58, mode: 'cold', variant: 'cold', name: "GS-8", name_ko: "그린란드 아빙기 GS-8", confidence: 'likely', note: "버뮤다 해팽의 Pa/Th가 아빙기마다 높아지고 δ13C가 낮아져, 뒤집힘이 약하고 얕았다 (Henry 2016). (뒷받침되나 단서가 있음)", refs: ["10.1126/science.aaf5529", "10.1016/j.quascirev.2014.09.007"] },
  { young: 36.58, old: 38.22, mode: 'warm', variant: 'nolab', name: "GI-8 (a-c)", name_ko: "그린란드 아간빙기 GI-8", confidence: 'likely', note: "Pa/Th와 δ13C가 오늘에 가까워 뒤집힘이 깊었고 (Henry 2016), 노르딕해에서 먼 바다 대류가 있었다 (Dokken & Jansen 1999). (뒷받침되나 단서가 있음)", refs: ["10.1126/science.aaf5529", "10.1038/46753", "10.1016/j.quascirev.2014.09.007"] },
  { young: 38.22, old: 39.9, mode: 'weak', variant: 'weak', name: "HS4 (GS-9)", name_ko: "하인리히 아빙기 4 (HS4)", confidence: 'likely', note: "버뮤다 해팽의 Pa/Th가 생성비에 이를 만큼 높아, 뒤집힘이 크게 약했다 (Henry 2016). (뒷받침되나 단서가 있음)", refs: ["10.1126/science.aaf5529", "10.5194/cp-10-2115-2014", "10.1016/j.quascirev.2014.09.007"] },
  { young: 39.9, old: 40.8, mode: 'cold', variant: 'cold', name: "GS-10 (GI-9 merged)", name_ko: "그린란드 아빙기 GS-10", confidence: 'likely', note: "버뮤다 해팽의 Pa/Th가 아빙기마다 높아지고 δ13C가 낮아져, 뒤집힘이 약하고 얕았다 (Henry 2016). (뒷받침되나 단서가 있음)", refs: ["10.1126/science.aaf5529", "10.1016/j.quascirev.2014.09.007"] },
  { young: 40.8, old: 41.46, mode: 'warm', variant: 'nolab', name: "GI-10", name_ko: "그린란드 아간빙기 GI-10", confidence: 'likely', note: "Pa/Th와 δ13C가 오늘에 가까워 뒤집힘이 깊었고 (Henry 2016), 노르딕해에서 먼 바다 대류가 있었다 (Dokken & Jansen 1999). (뒷받침되나 단서가 있음)", refs: ["10.1126/science.aaf5529", "10.1016/j.quascirev.2014.09.007"] },
  { young: 41.46, old: 42.24, mode: 'cold', variant: 'cold', name: "GS-11", name_ko: "그린란드 아빙기 GS-11", confidence: 'likely', note: "버뮤다 해팽의 Pa/Th가 아빙기마다 높아지고 δ13C가 낮아져, 뒤집힘이 약하고 얕았다 (Henry 2016). (뒷받침되나 단서가 있음)", refs: ["10.1126/science.aaf5529", "10.1016/j.quascirev.2014.09.007"] },
  { young: 42.24, old: 43.34, mode: 'warm', variant: 'nolab', name: "GI-11", name_ko: "그린란드 아간빙기 GI-11", confidence: 'likely', note: "Pa/Th와 δ13C가 오늘에 가까워 뒤집힘이 깊었고 (Henry 2016), 노르딕해에서 먼 바다 대류가 있었다 (Dokken & Jansen 1999). (뒷받침되나 단서가 있음)", refs: ["10.1126/science.aaf5529", "10.1016/j.quascirev.2014.09.007"] },
  { young: 43.34, old: 44.28, mode: 'cold', variant: 'cold', name: "GS-12", name_ko: "그린란드 아빙기 GS-12", confidence: 'likely', note: "버뮤다 해팽의 Pa/Th가 아빙기마다 높아지고 δ13C가 낮아져, 뒤집힘이 약하고 얕았다 (Henry 2016). (뒷받침되나 단서가 있음)", refs: ["10.1126/science.aaf5529", "10.1016/j.quascirev.2014.09.007"] },
  { young: 44.28, old: 46.86, mode: 'warm', variant: 'nolab', name: "GI-12 (a-c)", name_ko: "그린란드 아간빙기 GI-12", confidence: 'likely', note: "Pa/Th와 δ13C가 오늘에 가까워 뒤집힘이 깊었고 (Henry 2016), 노르딕해에서 먼 바다 대류가 있었다 (Dokken & Jansen 1999). (뒷받침되나 단서가 있음)", refs: ["10.1126/science.aaf5529", "10.1016/j.quascirev.2014.09.007"] },
  { young: 46.86, old: 48.34, mode: 'weak', variant: 'weak', name: "HS5 (GS-13)", name_ko: "하인리히 아빙기 5 (HS5)", confidence: 'likely', note: "버뮤다 해팽의 Pa/Th가 생성비에 이를 만큼 높아, 뒤집힘이 크게 약했다 (Henry 2016). (뒷받침되나 단서가 있음)", refs: ["10.1126/science.aaf5529", "10.5194/cp-10-2115-2014", "10.1016/j.quascirev.2014.09.007"] },
  { young: 48.34, old: 54.22, mode: 'warm', variant: 'nolab', name: "GI-13 to GI-14 (quasi-stadial GS-14 merged)", name_ko: "그린란드 아간빙기 GI-13–GI-14", confidence: 'likely', note: "Pa/Th와 δ13C가 오늘에 가까워 뒤집힘이 깊었고 (Henry 2016), 노르딕해에서 먼 바다 대류가 있었다 (Dokken & Jansen 1999). (뒷받침되나 단서가 있음)", refs: ["10.1126/science.aaf5529", "10.1016/j.quascirev.2014.09.007"] },
  { young: 54.22, old: 56.5, mode: 'cold', variant: 'cold', name: "GS-15 to GS-16.1 (HS5a?; GI-15.1, GI-15.2 merged)", name_ko: "그린란드 아빙기 GS-15–GS-16.1", confidence: 'likely', note: "버뮤다 해팽의 Pa/Th가 아빙기마다 높아지고 δ13C가 낮아져, 뒤집힘이 약하고 얕았다 (Henry 2016). (뒷받침되나 단서가 있음)", refs: ["10.1126/science.aaf5529", "10.5194/cp-10-2115-2014", "10.1016/j.quascirev.2014.09.007"] },
  { young: 56.5, old: 59.44, mode: 'warm', variant: 'nolab', name: "GI-16 to GI-17 (GS-16.2, GS-17.1, GS-17.2 merged)", name_ko: "그린란드 아간빙기 GI-16–GI-17", confidence: 'likely', note: "Pa/Th와 δ13C가 오늘에 가까워 뒤집힘이 깊었고 (Henry 2016), 노르딕해에서 먼 바다 대류가 있었다 (Dokken & Jansen 1999). (뒷받침되나 단서가 있음)", refs: ["10.1126/science.aaf5529", "10.1016/j.quascirev.2014.09.007"] },
  { young: 59.44, old: 63.84, mode: 'cold', variant: 'cold', name: "GS-18 (HS6)", name_ko: "그린란드 아빙기 GS-18 · HS6", confidence: 'debated', note: "HS6을 분해해 보여주는 기록이 없어 추운 상태로 두었다 (Guillevic 2014). (논쟁 중)", refs: ["10.5194/cp-10-2115-2014", "10.1126/science.aaf5529", "10.1038/nature14059", "10.1016/j.quascirev.2014.09.007"] },
  { young: 63.84, old: 70.38, mode: 'cold', variant: 'cold', name: "GS-19 / MIS 4 (GI-18, GI-19.1 merged)", name_ko: "MIS 4 빙기 (GS-19)", confidence: 'likely', note: "MIS 4 빙기. 이때부터 노르웨이해는 가라앉는 곳이 아니었다 (Duplessy 1988). 논쟁: 노르딕해에서 물이 계속 가라앉았다 (Stobbe 2025). (뒷받침되나 단서가 있음)", refs: ["10.1038/nature14059", "10.5194/cp-21-1281-2025", "10.1029/PA003i003p00343", "10.1016/j.quascirev.2014.09.007"] },
  { young: 70.38, old: 72.34, mode: 'warm', variant: 'nolab', name: "GI-19.2", name_ko: "그린란드 아간빙기 GI-19.2", confidence: 'likely', note: "깊고 강한 뒤집힘이 이어졌다 (Böhm 2015). (뒷받침되나 단서가 있음)", refs: ["10.1038/nature01090", "10.5194/cp-21-1281-2025", "10.1016/j.quascirev.2014.09.007"] },
  { young: 72.34, old: 74.1, mode: 'cold', variant: 'cold', name: "GS-20 (HS7a, minor)", name_ko: "그린란드 아빙기 GS-20", confidence: 'debated', note: "추운 상태는 유추다. 이 시기 대부분 깊은 뒤집힘이 강했다는 결과가 있다 (Böhm 2015). (논쟁 중)", refs: ["10.1038/nature14059", "10.5194/cp-10-2115-2014", "10.1029/2001PA000736", "10.1016/j.quascirev.2014.09.007"] },
  { young: 74.1, old: 76.44, mode: 'warm', variant: 'nolab', name: "GI-20 (a-c)", name_ko: "그린란드 아간빙기 GI-20", confidence: 'likely', note: "깊고 강한 뒤집힘이 이어졌다 (Böhm 2015). (뒷받침되나 단서가 있음)", refs: ["10.1038/nature01090", "10.5194/cp-21-1281-2025", "10.1016/j.quascirev.2014.09.007"] },
  { young: 76.44, old: 77.76, mode: 'cold', variant: 'cold', name: "GS-21.1 (HS7b, minor)", name_ko: "그린란드 아빙기 GS-21.1", confidence: 'debated', note: "추운 상태는 유추다. 이 시기 대부분 깊은 뒤집힘이 강했다는 결과가 있다 (Böhm 2015). (논쟁 중)", refs: ["10.1038/nature14059", "10.5194/cp-10-2115-2014", "10.1016/j.quascirev.2014.09.007"] },
  { young: 77.76, old: 85.06, mode: 'warm', variant: 'nolab', name: "GI-21 / ~MIS 5a (GS-21.2, GI-21.2 merged)", name_ko: "그린란드 아간빙기 GI-21 · MIS 5a", confidence: 'likely', note: "깊고 강한 뒤집힘이 이어졌다 (Böhm 2015). (뒷받침되나 단서가 있음)", refs: ["10.1038/nature01090", "10.5194/cp-21-1281-2025", "10.1016/j.quascirev.2014.09.007"] },
  { young: 85.06, old: 87.6, mode: 'cold', variant: 'cold', name: "GS-22 / ~MIS 5b (HS8, minor)", name_ko: "그린란드 아빙기 GS-22 · MIS 5b", confidence: 'debated', note: "추운 상태는 유추다. 이 시기 대부분 깊은 뒤집힘이 강했다는 결과가 있다 (Böhm 2015). (논쟁 중)", refs: ["10.1038/nature14059", "10.5194/cp-10-2115-2014", "10.5194/cp-21-1281-2025", "10.1016/j.quascirev.2014.09.007"] },
  { young: 87.6, old: 104.04, mode: 'warm', variant: 'nolab', name: "GI-22 to GI-23.1 / ~MIS 5c (quasi-stadial GS-23.1 merged)", name_ko: "그린란드 아간빙기 GI-22–GI-23.1 · MIS 5c", confidence: 'likely', note: "깊고 강한 뒤집힘이 이어졌다 (Böhm 2015). (뒷받침되나 단서가 있음)", refs: ["10.1038/nature01090", "10.5194/cp-21-1281-2025", "10.1016/j.quascirev.2014.09.007"] },
  { young: 104.04, old: 105.44, mode: 'cold', variant: 'cold', name: "GS-23.2 to GS-24.1 (HS9/HS10?, minor; GI-23.2 merged)", name_ko: "그린란드 아빙기 GS-23.2–GS-24.1", confidence: 'debated', note: "추운 상태는 유추다. 이 시기 대부분 깊은 뒤집힘이 강했다는 결과가 있다 (Böhm 2015). (논쟁 중)", refs: ["10.1038/nature14059", "10.5194/cp-10-2115-2014", "10.1016/j.quascirev.2014.09.007"] },
  { young: 105.44, old: 108.28, mode: 'warm', variant: 'nolab', name: "GI-24 (GS-24.2 merged)", name_ko: "그린란드 아간빙기 GI-24", confidence: 'likely', note: "깊고 강한 뒤집힘이 이어졌다 (Böhm 2015). (뒷받침되나 단서가 있음)", refs: ["10.1038/nature01090", "10.1016/j.quascirev.2014.09.007"] },
  { young: 108.28, old: 110.64, mode: 'cold', variant: 'cold', name: "GS-25 (late MIS 5d)", name_ko: "그린란드 아빙기 GS-25 · MIS 5d", confidence: 'debated', note: "추운 상태는 유추다. 이 시기 대부분 깊은 뒤집힘이 강했다는 결과가 있다 (Böhm 2015). (논쟁 중)", refs: ["10.1038/nature14059", "10.1029/PA003i003p00343", "10.1016/j.quascirev.2014.09.007"] },
  { young: 110.64, old: 115.37, mode: 'warm', variant: 'nolab', name: "GI-25 (a-c)", name_ko: "그린란드 아간빙기 GI-25", confidence: 'likely', note: "깊고 강한 뒤집힘이 이어졌다 (Böhm 2015). (뒷받침되나 단서가 있음)", refs: ["10.1038/nature01090", "10.1038/nature02805", "10.1016/j.quascirev.2014.09.007"] },
  { young: 115.37, old: 119.14, mode: 'cold', variant: 'cold', name: "GS-26 / last glacial inception", name_ko: "마지막 빙기의 시작 (GS-26)", confidence: 'debated', note: "약 11.5만 년 전 깊은 대서양 순환이 갑자기 약해졌으나 하인리히 수준에는 이르지 않았다 (Zhou 2025). 논쟁: 강한 순환이 이어졌다 (Böhm 2015). (논쟁 중)", refs: ["10.1038/s41467-025-62960-y", "10.1038/nature14059", "10.1073/pnas.1322103111", "10.1016/j.quascirev.2014.09.007"] },
  { young: 119.14, old: 125.0, mode: 'warm', variant: 'nolab', name: "MIS 5e / Last Interglacial (no Labrador sink)", name_ko: "최종 간빙기 (MIS 5e)", confidence: 'likely', note: "오늘과 비슷했으나 래브라도해에서는 깊은 물이 생기지 않았다 (Hillaire-Marcel 2001). 수백 년짜리 급감이 여러 번 있었는데, 1천 년 간격으로는 보이지 않는다 (Galaasen 2014). (뒷받침되나 단서가 있음)", refs: ["10.1126/science.1248667", "10.5194/cp-21-1281-2025", "10.1038/35074059", "10.1038/s41467-025-62960-y"] },
  { young: 125.0, old: 129.0, mode: 'warm', variant: 'nolab', name: "MIS 5e / Last Interglacial, early (convection possibly delayed)", name_ko: "최종 간빙기 초기 (MIS 5e)", confidence: 'debated', note: "간빙기 초기에는 환기가 약했고, 뒤집힘이 늦게 제 세기에 이르렀다 (Govin 2012; Jiménez-Amat & Zahn 2015). (논쟁 중)", refs: ["10.5194/cp-8-483-2012", "10.1002/2014PA002710", "10.1126/science.1248667", "10.1038/ncomms14595"] },
  { young: 129.0, old: 135.0, mode: 'weak', variant: 'weak', name: "HS11 / Termination II", name_ko: "하인리히 아빙기 11 (종말기 II)", confidence: 'likely', note: "뒤집힘이 거의 멈췄다는 결과 (McManus 2004)와, 약해졌지만 깊은 물이 계속 생겼다는 결과 (Gherardi 2009; Repschläger 2021)가 맞선다. (뒷받침되나 단서가 있음)", refs: ["10.1038/nature14499", "10.1038/ncomms14595", "10.1002/2014PA002710", "10.1038/nature14059"] },
];
