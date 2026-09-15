document.addEventListener('keydown', event => {
  if (event.key === 'Escape' && window.parent !== window) {
    window.parent.postMessage('close-collision', window.location.origin);
  }
});
