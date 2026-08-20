/* Мобильная навигация: меню сайта и боковое меню кабинета. */

function toggle(button, target, openClass) {
  if (!button || !target) return;
  button.addEventListener('click', () => {
    const open = target.classList.toggle(openClass);
    button.setAttribute('aria-expanded', open ? 'true' : 'false');
    button.classList.toggle('is-open', open);
  });
  // закрываем после перехода по ссылке
  target.addEventListener('click', (e) => {
    if (e.target.closest('a')) {
      target.classList.remove(openClass);
      button.setAttribute('aria-expanded', 'false');
      button.classList.remove('is-open');
    }
  });
}

toggle(document.getElementById('nav-toggle'), document.getElementById('pub-menu'), 'is-open');
toggle(document.getElementById('side-toggle'), document.getElementById('cabinet-side'), 'is-open');
