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

// Колокольчик уведомлений в кабинете: открыть/закрыть, клик мимо и Esc закрывают
(() => {
  const bell = document.getElementById('bell-toggle');
  const panel = document.getElementById('bell-panel');
  if (!bell || !panel) return;

  const setOpen = (open) => {
    panel.hidden = !open;
    bell.setAttribute('aria-expanded', open ? 'true' : 'false');
  };

  bell.addEventListener('click', (e) => {
    e.stopPropagation();
    setOpen(panel.hidden);
    if (!panel.hidden) panel.querySelector('a')?.focus({ preventScroll: true });
  });
  document.addEventListener('click', (e) => {
    if (!panel.hidden && !panel.contains(e.target)) setOpen(false);
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !panel.hidden) { setOpen(false); bell.focus(); }
  });
})();

// Переключатель темы: светлая ↔ тёмная, выбор запоминается в браузере
document.querySelectorAll('[data-theme-toggle]').forEach((btn) => {
  const root = document.documentElement;
  const sync = () => {
    const light = root.getAttribute('data-theme') === 'light';
    btn.setAttribute('aria-pressed', light ? 'true' : 'false');
    btn.title = light ? 'Тёмная тема' : 'Светлая тема';
  };
  sync();
  btn.addEventListener('click', () => {
    const light = root.getAttribute('data-theme') !== 'light';
    root.classList.add('theme-anim');
    if (light) root.setAttribute('data-theme', 'light'); else root.removeAttribute('data-theme');
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', light ? '#F3F4F6' : '#0A0B0D');
    try { localStorage.setItem('aero-theme', light ? 'light' : 'dark'); } catch (e) {}
    sync();
    setTimeout(() => root.classList.remove('theme-anim'), 320);
  });
});
