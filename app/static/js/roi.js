/* ROI-калькулятор: экономика эксплуатации агродрона.
   Модель затрат: экипаж и энергия за смену + ресурс аккумуляторов, ТО и логистика на гектар.
   Стоимость СЗР и семян в расчёт не входит — она одинакова для любого способа обработки. */

const CREW_DAY = 13000;      // экипаж + топливо генератора, ₽/день
const SERVICE_HA = 45;       // ТО, форсунки, расходники, ₽/га
const BATTERY_HA = 35;       // ресурс аккумуляторов, ₽/га
const LOGISTICS_HA = 20;     // переезды между полями, ₽/га
const MONTHLY_FIXED = 100000; // хранение, страхование, ПО, сервисный контракт, ₽/мес
const MONTHS = 24;

const $ = (id) => document.getElementById(id);

// Для T50 своего снимка нет — показываем ближайший по классу T70
const PHOTOS = { t25: 't25', t50: 't70', t70: 't70', t100: 't100' };

let mode = 'own';

function setPhoto(modelKey) {
  const key = PHOTOS[modelKey] || 't100';
  const img = $('unit-img');
  const src = $('unit-src');
  if (img) img.src = `/static/img/drone-${key}.png`;
  if (src) src.srcset = `/static/img/drone-${key}.webp`;
}

function num(id) {
  const raw = $(id).value.replace(/[^\d.-]/g, '');
  const value = parseFloat(raw);
  return isNaN(value) ? 0 : value;
}

function fmtInt(value) {
  return Math.round(value).toLocaleString('ru-RU').replace(/ /g, ' ');
}

function fmtMln(value) {
  return (value / 1e6).toFixed(2).replace('.', ',');
}

function state() {
  const modelOpt = $('p-model').selectedOptions[0];
  const cropOpt = $('p-crops').selectedOptions[0];
  const rate = parseFloat(cropOpt.dataset.rate) || 1;
  const perf = (parseFloat(modelOpt.dataset.perf) || 145) / rate;

  const area = Math.max(0, num('p-area'));
  const passes = Math.max(1, num('p-passes'));
  const price = Math.max(0, num('p-price'));
  const days = Math.max(1, num('p-days'));

  const capex = parseFloat(modelOpt.dataset.price) || 0;
  const costPerHa = CREW_DAY / perf + SERVICE_HA + BATTERY_HA + LOGISTICS_HA;
  const totalHa = area * passes;
  const after = totalHa * costPerHa;
  const saving = totalHa * (price - costPerHa);
  const netMonthly = saving / 12 - MONTHLY_FIXED;
  const payback = netMonthly > 0 ? capex / netMonthly : null;

  return {
    modelName: modelOpt.dataset.name, cropLabel: cropOpt.textContent.trim(),
    area, passes, price, days, capex, perf, costPerHa, totalHa, after, saving, netMonthly, payback,
  };
}

function render() {
  const s = state();

  $('roi-title').textContent = 'Экономика эксплуатации ' + s.modelName;
  $('unit-name').textContent = s.modelName;
  setPhoto($('p-model').value);
  $('s-area').textContent = fmtInt(s.area) + ' га';
  $('s-passes').textContent = fmtInt(s.passes);
  $('s-price').textContent = fmtInt(s.price) + ' ₽/га';
  $('s-days').textContent = fmtInt(s.days) + ' дней';

  $('price-label').innerHTML = (mode === 'own'
    ? 'Текущая стоимость гектара'
    : 'Цена услуги за гектар')
    + ' <span class="hint" title="Ставка, с которой сравнивается работа собственным дроном.">i</span>';
  $('r-saving-label').textContent = mode === 'own' ? 'Экономия за сезон' : 'Доход за сезон';

  $('r-cost').innerHTML = fmtInt(s.costPerHa) + ' <small>₽ / га</small>';
  $('r-saving').innerHTML = fmtMln(s.saving) + ' <small>млн ₽</small>';
  $('r-after').innerHTML = fmtMln(s.after) + ' <small>млн ₽</small>';
  $('r-payback').innerHTML = s.payback
    ? Math.round(s.payback) + ' <small>месяцев</small>'
    : '— <small>не окупается</small>';

  const shifts = s.totalHa / s.perf;
  const loadNote = shifts > s.days
    ? `Расчётная загрузка ${fmtInt(shifts)} смен превышает сезон ${fmtInt(s.days)} дней — потребуется вторая машина или экипаж.`
    : `Расчётная загрузка ${fmtInt(shifts)} смен из ${fmtInt(s.days)} дней сезона.`;
  const note = document.querySelector('.roi-note');
  note.dataset.load = loadNote;
  note.textContent = loadNote + ' Учитываются экипаж, ресурс аккумуляторов, ТО и логистика; '
    + 'стоимость СЗР и семян не включена. Результат сохраняется в личном кабинете.';

  drawChart(s);
}

function drawChart(s) {
  const svg = $('roi-chart');
  const W = 760, H = 320;
  const padL = 62, padR = 18, padT = 16, padB = 38;
  const plotW = W - padL - padR, plotH = H - padT - padB;

  const points = [];
  for (let m = 0; m <= MONTHS; m++) points.push(-s.capex + s.netMonthly * m);

  const maxV = Math.max(...points, 0);
  const minV = Math.min(...points, 0);
  const span = (maxV - minV) || 1;
  const top = maxV + span * 0.12;
  const bottom = minV - span * 0.12;

  const x = (m) => padL + (plotW * m) / MONTHS;
  const y = (v) => padT + plotH * (1 - (v - bottom) / (top - bottom));

  const parts = [];

  // сетка и подписи оси Y
  const ticks = 6;
  for (let i = 0; i <= ticks; i++) {
    const v = bottom + ((top - bottom) * i) / ticks;
    const yy = y(v).toFixed(1);
    parts.push(`<line x1="${padL}" y1="${yy}" x2="${W - padR}" y2="${yy}" stroke="#23262D" stroke-width="1"/>`);
    parts.push(`<text x="${padL - 10}" y="${yy}" text-anchor="end" dominant-baseline="middle"
      font-family="JetBrains Mono, monospace" font-size="10" fill="#5B6270">${(v / 1e6).toFixed(0)}</text>`);
  }
  parts.push(`<text x="14" y="${padT + plotH / 2}" text-anchor="middle" font-size="10" fill="#5B6270"
    font-family="Inter, sans-serif" transform="rotate(-90 14 ${padT + plotH / 2})">млн ₽</text>`);

  // нулевая линия
  parts.push(`<line x1="${padL}" y1="${y(0).toFixed(1)}" x2="${W - padR}" y2="${y(0).toFixed(1)}"
    stroke="#34383F" stroke-width="1"/>`);

  // ось X
  for (let m = 0; m <= MONTHS; m++) {
    if (m % 2 !== 0) continue;
    parts.push(`<text x="${x(m).toFixed(1)}" y="${H - 14}" text-anchor="middle"
      font-family="JetBrains Mono, monospace" font-size="10" fill="#5B6270">${m}</text>`);
  }
  parts.push(`<text x="${padL + plotW / 2}" y="${H - 1}" text-anchor="middle" font-size="10"
    fill="#5B6270" font-family="Inter, sans-serif">Месяц</text>`);

  // линия денежного потока
  const path = points.map((v, m) => `${m === 0 ? 'M' : 'L'}${x(m).toFixed(1)},${y(v).toFixed(1)}`).join(' ');
  parts.push(`<path d="${path}" fill="none" stroke="#FF6A1A" stroke-width="2"/>`);
  points.forEach((v, m) => {
    parts.push(`<circle cx="${x(m).toFixed(1)}" cy="${y(v).toFixed(1)}" r="2.6" fill="#FF6A1A"/>`);
  });

  // точка окупаемости
  if (s.payback && s.payback <= MONTHS) {
    const px = x(s.payback), py = y(0);
    parts.push(`<line x1="${px.toFixed(1)}" y1="${padT}" x2="${px.toFixed(1)}" y2="${padT + plotH}"
      stroke="#FF6A1A" stroke-width="1" stroke-dasharray="4 4" opacity="0.7"/>`);
    parts.push(`<circle cx="${px.toFixed(1)}" cy="${py.toFixed(1)}" r="6" fill="none"
      stroke="#FF6A1A" stroke-width="2"/>`);
    const label = `Окупаемость · ${Math.round(s.payback)} месяцев`;
    const boxW = label.length * 6.2 + 20;
    const boxX = Math.min(px + 12, W - padR - boxW);
    parts.push(`<rect x="${boxX.toFixed(1)}" y="${(py + 12).toFixed(1)}" width="${boxW.toFixed(1)}" height="24"
      fill="#1A1D22" stroke="#34383F"/>`);
    parts.push(`<text x="${(boxX + boxW / 2).toFixed(1)}" y="${(py + 28).toFixed(1)}" text-anchor="middle"
      font-size="11" fill="#F2F3F5" font-family="Inter, sans-serif">${label}</text>`);
  }

  // стартовая точка
  parts.push(`<text x="${x(0) + 6}" y="${(y(points[0]) + 16).toFixed(1)}"
    font-family="JetBrains Mono, monospace" font-size="10" fill="#FF6A1A">${fmtMln(points[0])}</text>`);

  svg.innerHTML = parts.join('');
}

// ===== события =====
document.querySelectorAll('#mode-seg button').forEach((btn) => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('#mode-seg button').forEach((b) => b.classList.remove('on'));
    btn.classList.add('on');
    mode = btn.dataset.mode;
    render();
  });
});

document.querySelectorAll('.stepper button').forEach((btn) => {
  btn.addEventListener('click', () => {
    const input = $(btn.dataset.target);
    const step = parseFloat(btn.dataset.step);
    const value = Math.max(0, (parseFloat(input.value.replace(/[^\d.-]/g, '')) || 0) + step);
    input.value = fmtInt(value);
    render();
  });
});

['p-area', 'p-passes', 'p-price', 'p-days'].forEach((id) => {
  $(id).addEventListener('input', render);
  $(id).addEventListener('blur', () => { $(id).value = fmtInt(num(id)); render(); });
});
['p-model', 'p-crops'].forEach((id) => $(id).addEventListener('change', render));

$('roi-save').addEventListener('click', async () => {
  const s = state();
  const body = new FormData();
  body.append('mode', mode);
  body.append('area', s.area);
  body.append('crops', s.cropLabel);
  body.append('passes', s.passes);
  body.append('price_per_ha', s.price);
  body.append('season_days', s.days);
  body.append('cost_per_ha', Math.round(s.costPerHa));
  body.append('season_saving', Math.round(s.saving));
  body.append('payback_months', s.payback ? s.payback.toFixed(1) : 0);
  try {
    const res = await fetch('/roi/save', { method: 'POST', body });
    $('roi-save-note').textContent = res.ok
      ? 'Расчёт сохранён. Менеджер увидит его вместе с заявкой.'
      : 'Не удалось сохранить расчёт.';
  } catch (e) {
    $('roi-save-note').textContent = 'Не удалось сохранить расчёт.';
  }
});

render();
