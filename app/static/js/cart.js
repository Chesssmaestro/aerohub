document.addEventListener('click', (e) => {
  const btn = e.target.closest('.stepper button[data-step]');
  if (!btn) return;
  const input = btn.parentElement.querySelector('input[type="number"]');
  if (!input) return;
  const step = parseInt(btn.dataset.step, 10);
  const min = parseInt(input.min || '1', 10);
  const max = parseInt(input.max || '999', 10);
  const value = Math.min(max, Math.max(min, (parseInt(input.value, 10) || min) + step));
  input.value = value;
});
