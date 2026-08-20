/* Конфигуратор комплектации: платформа + пакет + опции → спецификация и стоимость. */

const PACKAGE_NOTES = {
  base: 'Опрыскивание, один комплект аккумуляторов, базовый комплект документов.',
  pro: 'Опрыскивание и грузы, RTK, зарядная станция, обучение двух операторов.',
  max: 'Все сценарии работы, комплект для гранул, два комплекта аккумуляторов.',
};

// Для T50 своего снимка нет — показываем ближайший по классу T70
const PHOTOS = { t25: 't25', t50: 't70', t70: 't70', t100: 't100' };

const money = (v) => Math.round(v).toLocaleString('ru-RU').replace(/ /g, ' ') + ' ₽';

function setPhoto(modelKey) {
  const key = PHOTOS[modelKey] || 't100';
  const img = document.getElementById('cfg-img');
  const src = document.getElementById('cfg-src');
  if (img) img.src = `/static/img/drone-${key}.png`;
  if (src) src.srcset = `/static/img/drone-${key}.webp`;
}

function render() {
  const model = document.getElementById('cfg-model').selectedOptions[0];
  const pack = document.getElementById('cfg-package').selectedOptions[0];
  const opts = [...document.querySelectorAll('.cfg-opt')];

  document.getElementById('cfg-title').textContent = 'Конфигурация ' + model.dataset.name;
  setPhoto(model.value);
  document.getElementById('cfg-tank').textContent = model.dataset.tank;
  document.getElementById('cfg-width').textContent = model.dataset.width;
  document.getElementById('cfg-shift').textContent = model.dataset.shift;
  document.getElementById('cfg-package-note').textContent = PACKAGE_NOTES[pack.value] || '';

  let total = parseFloat(model.dataset.price) + parseFloat(pack.dataset.extra);
  const rows = [
    { name: model.dataset.name + ' — базовая платформа', price: parseFloat(model.dataset.price) },
    { name: 'Пакет «' + pack.dataset.name + '»', price: parseFloat(pack.dataset.extra) },
  ];

  opts.forEach((opt) => {
    opt.closest('.opt-row').querySelector('.opt-box').classList.toggle('on', opt.checked);
    opt.closest('.opt-row').querySelector('.opt-box').textContent = opt.checked ? '✓' : '';
    if (opt.checked) {
      total += parseFloat(opt.dataset.price);
      rows.push({ name: opt.dataset.name, price: parseFloat(opt.dataset.price) });
    }
  });

  document.getElementById('cfg-total').textContent = money(total);
  document.getElementById('cfg-count').textContent = rows.filter((r) => r.price > 0).length + ' позиций';
  document.getElementById('cfg-spec').innerHTML = rows
    .map((r) => `<div class="doc-row"><span>${r.name}</span>
      <span class="doc-status ${r.price ? '' : 'dim'}">${r.price ? money(r.price) : 'включено'}</span></div>`)
    .join('');

  document.getElementById('cfg-preset').value =
    `Комплектация ${model.dataset.name}, пакет «${pack.dataset.name}»: `
    + rows.slice(2).map((r) => r.name).join(', ')
    + `. Ориентировочная стоимость ${money(total)}.`;
}

document.getElementById('cfg-model').addEventListener('change', render);
document.getElementById('cfg-package').addEventListener('change', render);
document.querySelectorAll('.cfg-opt').forEach((o) => o.addEventListener('change', render));

render();
