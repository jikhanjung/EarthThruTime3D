import { INDIA_ASIA } from './interior-cutaway.js';
// One display cut shared by the independently enabled crust and mantle layers.
export function createInteriorControls({ focus }) {
  const get = id => document.getElementById(`interior-${id}`);
  if (!get('cutaway')) return null;
  const listeners = new Set();
  const read = () => ({
    enabled: get('cutaway').checked,
    west: Number(get('west').value), east: Number(get('east').value),
    south: Number(get('south').value), north: Number(get('north').value),
  });
  function notify() {
    for (const name of ['west', 'east', 'south', 'north']) {
      get(`${name}-value`).textContent = get(name).value + '°';
    }
    for (const listener of listeners) listener(read());
  }
  for (const name of ['cutaway', 'west', 'east', 'south', 'north']) {
    get(name).addEventListener('input', () => {
      if (name === 'south' && Number(get('south').value) >= Number(get('north').value)) get('south').value = Number(get('north').value) - 1;
      if (name === 'north' && Number(get('north').value) <= Number(get('south').value)) get('north').value = Number(get('south').value) + 1;
      notify();
    });
  }
  get('india-asia').addEventListener('click', () => {
    for (const [name, value] of Object.entries(INDIA_ASIA)) get(name).value = value;
    notify();
  });
  get('focus').addEventListener('click', () => focus(read()));
  return {
    read,
    subscribe(listener) { listeners.add(listener); },
    onProjection(name) { get('section-controls').disabled = name !== 'globe'; },
  };
}
