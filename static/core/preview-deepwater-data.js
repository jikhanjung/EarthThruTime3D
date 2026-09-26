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
      { level: 'likely', warm: true, at: [-55, 5.5], name: '막힌 원시 북대서양의 따뜻하고 짠 물' },
    ],
    note: '남쪽 고위도(인도양 쪽, 남태평양)에서 깊은 물이 생겼을 가능성이 크다 (Murphy 2012; Poulsen 2001; Donnadieu 2016). 북태평양은 모형 결과뿐이다 (Donnadieu 2016). 막혀 있던 원시 북대서양은 저위도·테티스에서 온 20–25 °C의 따뜻하고 짠 물로 찼다 (Friedrich 2008; Martin 2012; Liu 2023). 논쟁: 따뜻하고 짠 물이 전 지구의 주된 방식이었는지 (Brass 1982 / Murphy 2012).',
  },
};
