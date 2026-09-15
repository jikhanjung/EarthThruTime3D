const dialog = document.getElementById('collision-dialog');
const iframe = dialog.querySelector('iframe');
const buttons = [...document.querySelectorAll('[data-collision-open]')];
let opener;
buttons.forEach(button => button.addEventListener('click', () => {
  opener = button;
  if (dialog.open) { dialog.close(); return; }
  iframe.src = iframe.dataset.src;
  dialog.showModal();
  button.setAttribute('aria-expanded', 'true');
}));
dialog.addEventListener('close', () => {
  // Tear down the child animation and requests when hidden; cached data survives.
  iframe.removeAttribute('src');
  buttons.forEach(button => button.setAttribute('aria-expanded', 'false'));
  opener?.focus();
});
window.addEventListener('message', event => {
  if (event.origin === location.origin && event.source === iframe.contentWindow && event.data === 'close-collision') {
    dialog.close();
  }
});
