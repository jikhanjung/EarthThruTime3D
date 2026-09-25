// Short climate and biotic events as marks over the timeline. The model maps are
// snapshots several Myr apart on a smooth CO2 curve, so an event shorter than the gap
// between them cannot show on the surface; a mark says where it was and what the record
// shows. Ages in Ma (the time windows' ka are Ma / 1000). Dates and citations are checked
// in climate-events-data.js (devlog wwolf 019), not guessed here.
export const KINDS = {
  wet: { colour: '#01665e', letter: 'W' },
  dry: { colour: '#bf812d', letter: 'D' },
  warm: { colour: '#b8211c', letter: 'H' },
  cold: { colour: '#2945a8', letter: 'C' },
  glaciation: { colour: '#2945a8', letter: 'I' },
  anoxic: { colour: '#6a3d9a', letter: 'A' },
  extinction: { colour: '#333333', letter: 'X' },
};

export let EVENTS = [];
export function setEvents(list) { EVENTS = list; }

// Fractional slider index of an age: stops run oldest first and are not evenly spaced
// in age, so interpolate between the two stops that bracket it.
export function fractionalIndex(stops, age) {
  const last = stops.length - 1;
  if (age >= stops[0][3]) return 0;
  if (age <= stops[last][3]) return last;
  for (let i = 0; i < last; i++) {
    const older = stops[i][3], younger = stops[i + 1][3];
    if (age <= older && age >= younger) return i + (older - age) / (older - younger || 1);
  }
  return last;
}

// Events whose span, widened by half a stop gap either side, holds the stop's age.
export function eventsAt(stops, index) {
  const age = stops[index][3];
  const gap = Math.abs((stops[Math.max(0, index - 1)][3] - stops[Math.min(stops.length - 1, index + 1)][3]) / 2) || 0;
  const windowed = stops[0][3] < 1;
  return EVENTS.filter(event => (windowed ? event.start_ma < 1 : event.start_ma >= 1)
    && age <= event.start_ma + gap / 2 && age >= event.end_ma - gap / 2);
}

export function drawEventMarks(container, stops, lang, onPick) {
  if (!container) return;
  container.replaceChildren();
  const last = stops.length - 1;
  // The whole timeline leaves the thousand-year events to the time windows, where they
  // have room; a window shows only its own.
  const windowed = stops[0][3] < 1;
  const inRange = EVENTS.filter(event => event.end_ma <= stops[0][3] && event.start_ma >= stops[last][3]
    && (windowed ? event.start_ma < 1 : event.start_ma >= 1));
  for (const event of inRange) {
    const a = fractionalIndex(stops, event.start_ma) / last;
    const b = fractionalIndex(stops, event.end_ma) / last;
    const kind = KINDS[event.kind[0]] ?? KINDS.extinction;
    const mark = document.createElement('button');
    mark.type = 'button';
    mark.className = 'event-mark';
    mark.style.left = `${(a * 100).toFixed(3)}%`;
    mark.style.width = `max(8px, ${((b - a) * 100).toFixed(3)}%)`;
    mark.style.background = kind.colour;
    mark.textContent = kind.letter;
    const name = displayName(event, lang);
    mark.title = `${name} · ${spanText(event)}`;
    mark.setAttribute('aria-label', mark.title);
    mark.addEventListener('click', () => onPick(Math.round(fractionalIndex(stops, event.peak_ma ?? (event.start_ma + event.end_ma) / 2))));
    container.append(mark);
  }
  container.hidden = inRange.length === 0;
}

// Enough decimals that the two ends of a span read apart: a 60 kyr event at 252 Ma
// needs three, a two-million-year one none.
export function spanText(event) {
  const [scale, unit] = event.start_ma < 1 ? [1000, 'ka'] : [1, 'Ma'];
  const span = (event.start_ma - event.end_ma) * scale;
  const digits = span > 0 ? Math.max(0, Math.min(3, Math.ceil(-Math.log10(span)) + 1)) : 2;
  const f = value => `${+(value * scale).toFixed(digits)}`;
  return span === 0 ? `${f(event.start_ma)} ${unit}` : `${f(event.start_ma)}–${f(event.end_ma)} ${unit}`;
}
const displayName = (event, lang) => (lang === 'ko' && event.name_ko ? event.name_ko : event.name).replace(/\*$/, '');

// The note under the timeline while the slider sits inside one or more events.
export function describeEvents(note, stops, index, lang) {
  if (!note) return;
  const found = eventsAt(stops, index);
  note.hidden = found.length === 0;
  note.replaceChildren();
  for (const event of found) {
    const line = document.createElement('p');
    const name = displayName(event, lang);
    const strong = document.createElement('strong');
    strong.textContent = `${name} (${spanText(event)})`;
    const what = lang === 'ko' && event.what_ko ? event.what_ko : event.what;
    const caveat = lang === 'ko'
      ? ' 지도는 이 사건보다 성긴 간격의 모형 스냅숏이라 표면에 이 사건이 따로 보이지 않습니다.'
      : ' The maps are model snapshots spaced wider than this event, so the surface does not show it.';
    line.append(strong, ` ${what}${event.snapshot_caveat === false ? '' : caveat} `);
    for (const cite of event.cites ?? []) {
      const link = document.createElement('a');
      link.href = `https://doi.org/${cite.doi}`;
      link.target = '_blank';
      link.rel = 'noopener';
      link.textContent = cite.short;
      line.append(link, ' ');
    }
    note.append(line);
  }
}
