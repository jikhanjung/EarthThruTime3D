const $ = (id) => document.getElementById(id);

export function closestFrame(frames, age) {
  return frames.reduce((a, b) => (Math.abs(b.age_ma - age) < Math.abs(a.age_ma - age) ? b : a));
}

// Coordinates the selected age and its controls. Rendering belongs to scene;
// shared timeline, camera and page controls are accessed through the globe bridge.
export function createMantleOverlay({ config, stage, scene, globe }) {
  if (!config || !$('mantle-overlay')) return null;
  const toggle = $('mantle-overlay');
  const options = $('mantle-overlay-options');
  const caption = $('mantle-overlay-caption');
  const status = $('mantle-overlay-status');
  const retry = $('mantle-overlay-retry');
  let active = false;
  let saved = null;
  let controller = null;
  let debounce = null;
  let frame = config.frames[0];
  let ready = false;

  function message(text) {
    const formatted = text.replace('{age}', String(frame.age_ma));
    status.textContent = formatted;
    caption.textContent = formatted;
  }

  function linkedState() {
    document.dispatchEvent(
      new CustomEvent('globe-section-state', {
        detail: {
          active,
          ready,
          age: frame.age_ma,
          error: stage.dataset.mantleOverlay === 'error',
        },
      }),
    );
  }

  function visibility() {
    // Loading changes readiness for controls, not the last complete globe.
    const rendered = scene.update({
      active,
      opacity: Number($('mantle-opacity').value) / 100,
      cutaway: $('mantle-cutaway').checked,
      layers: {
        slabs: $('overlay-slabs').checked,
        piles: $('overlay-piles').checked,
        core: $('overlay-core').checked,
      },
      showSection: $('mantle-section').checked,
    });
    stage.dataset.mantleCutaway = String(rendered.cutaway);
    stage.dataset.mantleOpacity = String(rendered.opacity);
  }

  function cutPosition() {
    scene.setCutaway({
      longitude: Number($('mantle-longitude').value),
      latitude: Number($('mantle-latitude').value),
      radius: Number($('mantle-radius').value),
    });
    for (const id of ['longitude', 'latitude', 'radius']) {
      $(`mantle-${id}-value`).textContent = $(`mantle-${id}`).value + '°';
    }
    $('mantle-opacity-value').textContent = $('mantle-opacity').value + '%';
    visibility();
  }

  function leave(restorePrevious = true) {
    if (!active) return;
    active = false;
    ready = false;
    controller?.abort();
    controller = null;
    clearTimeout(debounce);
    scene.clear();
    toggle.checked = false;
    options.hidden = true;
    retry.hidden = true;
    caption.hidden = true;
    globe.setPlaybackEnabled(true);
    stage.dataset.mantleOverlay = 'off';
    delete stage.dataset.mantleAge;
    visibility();
    linkedState();
    const previous = saved;
    saved = null;
    if (restorePrevious && previous) globe.restore(previous);
  }

  async function load(first = false) {
    controller?.abort();
    const pending = new AbortController();
    controller = pending;
    const selected = frame;
    ready = false;
    stage.dataset.mantleOverlay = 'loading';
    visibility();
    linkedState();
    message(config.strings.loading);
    retry.hidden = true;
    caption.hidden = false;
    let prepared = null;
    const isCurrent = () => !pending.signal.aborted && active;
    try {
      const prepare = async () => {
        prepared = await scene.prepare(selected, pending.signal);
        if (!isCurrent()) {
          prepared.dispose();
          throw new DOMException('Superseded', 'AbortError');
        }
        return () => {
          prepared.commit();
          visibility();
          stage.dataset.mantleAge = String(selected.age_ma);
        };
      };
      await globe.enter(selected.age_ma, first, { prepare, isCurrent });
      if (!isCurrent()) {
        prepared?.dispose();
        return;
      }
      ready = true;
      visibility();
      stage.dataset.mantleOverlay = 'ready';
      stage.dataset.mantleAge = String(selected.age_ma);
      $('mantle-age').value = String(selected.age_ma);
      $('mantle-residual').textContent = config.strings.residual.replace(
        '{error}',
        selected.india_position_p95_deg.toFixed(2),
      );
      message(config.strings.ready);
      linkedState();
      if (first) globe.collapseInfoOnMobile();
    } catch (error) {
      prepared?.dispose();
      if (isCurrent()) {
        pending.abort();
        ready = false;
        scene.clear();
        visibility();
        stage.dataset.mantleOverlay = 'error';
        delete stage.dataset.mantleAge;
        linkedState();
        message(config.strings.error);
        retry.hidden = false;
      }
    }
  }

  function requestAge(age) {
    if (!active) return false;
    if (!Number.isFinite(age) || age < 0 || age > 80) {
      leave(false);
      return false;
    }
    const next = closestFrame(config.frames, age);
    if (next === frame && ready) {
      // Exact-age calls can change surface options. An in-between age must stay
      // snapped without falling through to selectStop with unsynchronised terrain.
      if (age === frame.age_ma) return false;
      globe.snapTimeline(frame.age_ma);
      return true;
    }
    controller?.abort();
    clearTimeout(debounce);
    frame = next;
    ready = false;
    stage.dataset.mantleOverlay = 'loading';
    visibility();
    linkedState();
    message(config.strings.loading);
    $('mantle-age').value = String(frame.age_ma);
    debounce = setTimeout(() => load(), 180);
    return true;
  }

  toggle.addEventListener('change', () => {
    if (!toggle.checked) {
      leave();
      return;
    }
    saved = globe.capture();
    active = true;
    globe.setPlaybackEnabled(false);
    frame = config.frames[0];
    options.hidden = false;
    cutPosition();
    load(true);
  });
  retry.addEventListener('click', () => load());
  $('mantle-age').addEventListener('change', () => requestAge(Number($('mantle-age').value)));
  for (const id of [
    'mantle-cutaway',
    'overlay-slabs',
    'overlay-piles',
    'overlay-core',
    'mantle-section',
  ]) {
    $(id).addEventListener('change', visibility);
  }
  for (const id of ['longitude', 'latitude', 'radius', 'opacity']) {
    $(`mantle-${id}`).addEventListener('input', cutPosition);
  }
  $('mantle-focus').addEventListener('click', () => globe.focus(scene.focusPoint()));
  document.addEventListener('globe-section-age', (event) => {
    if (active && config.frames.some((entry) => entry.age_ma === event.detail.age)) {
      requestAge(event.detail.age);
    }
  });
  let down;
  stage.addEventListener('pointerdown', (event) => {
    down = [event.clientX, event.clientY];
  });
  stage.addEventListener('pointerup', (event) => {
    if (
      !active ||
      !ready ||
      !down ||
      Math.hypot(event.clientX - down[0], event.clientY - down[1]) > 5
    )
      return;
    if (
      scene.sectionHit(
        event.clientX,
        event.clientY,
        stage.getBoundingClientRect(),
        globe.getCamera(),
      )
    ) {
      $('mantle-section-open').click();
    }
  });
  stage.dataset.mantleOverlay = 'off';
  return {
    leave,
    requestAge,
    isActive: () => active,
    neighbourAge: (direction) =>
      active
        ? config.frames[
            Math.max(
              0,
              Math.min(config.frames.length - 1, config.frames.indexOf(frame) + direction),
            )
          ].age_ma
        : null,
    onProjection: (name) => {
      if (active && name !== 'globe') leave(false);
    },
    cutsPoint: scene.cutsPoint,
  };
}
