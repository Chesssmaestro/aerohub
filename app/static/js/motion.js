/* Движение портала: GSAP + ScrollTrigger, плавный скролл Lenis только на публичных страницах.
   Правила — в DESIGN.md: только transform / opacity (и stroke-dashoffset маршрута),
   300–700 мс, power2/power3.out, всё проигрывается один раз.
   Без библиотек или при prefers-reduced-motion скрипт ничего не делает — контент уже виден
   (класс js-motion снимает инлайн-скрипт в base.html). */

(function () {
  const root = document.documentElement;
  const gsap = window.gsap;
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduce || !gsap) {
    root.classList.remove('js-motion');
    return;
  }
  window.AERO_MOTION = true;

  const ScrollTrigger = window.ScrollTrigger;
  if (ScrollTrigger) gsap.registerPlugin(ScrollTrigger);
  gsap.defaults({ ease: 'power3.out', duration: 0.6 });

  const isPublic = !!document.querySelector('.pubnav');
  const $$ = (sel, ctx) => Array.from((ctx || document).querySelectorAll(sel));

  /* ---------- Плавный скролл (только сайт; в кабинетах нативный) ---------- */
  if (isPublic && window.Lenis) {
    const lenis = new window.Lenis({
      duration: 1.05,
      easing: (t) => 1 - Math.pow(1 - t, 3),
    });
    if (ScrollTrigger) lenis.on('scroll', ScrollTrigger.update);
    gsap.ticker.add((time) => lenis.raf(time * 1000));
    gsap.ticker.lagSmoothing(0);

    // Ссылки меню вида «/#spraying» на этой же странице — плавно, с отступом под шапку
    // из scroll-margin-top в CSS, чтобы нативный и плавный переходы совпадали.
    document.addEventListener('click', (e) => {
      const a = e.target.closest('a[href*="#"]');
      if (!a || e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey) return;
      const url = new URL(a.href, location.href);
      if (url.pathname !== location.pathname || !url.hash) return;
      const target = document.getElementById(decodeURIComponent(url.hash.slice(1)));
      if (!target) return;
      e.preventDefault();
      // Цель считаем от фактической позиции: клик посреди инерции колеса не должен сбивать точку
      const margin = parseFloat(getComputedStyle(target).scrollMarginTop) || 0;
      lenis.scrollTo(target.getBoundingClientRect().top + window.scrollY - margin);
      history.pushState(null, '', url.hash);
    });
  }

  /* ---------- Hero: заголовок по строкам, затем текст, кнопки и дрон ---------- */
  const hero = document.querySelector('.hero');
  if (hero) {
    const h1 = hero.querySelector('h1');
    let lines = [];
    if (h1) {
      // Делим заголовок по <br> на строки-маски; текст не меняется.
      const parts = h1.innerHTML.split(/<br\s*\/?>/i);
      h1.innerHTML = parts
        .map((p) => '<span class="line"><span class="line-in">' + p.trim() + '</span></span>')
        .join(' ');
      lines = $$('.line-in', h1);
      gsap.set(h1, { opacity: 1 });
      gsap.set(lines, { yPercent: 105 });
    }

    const tl = gsap.timeline({ delay: 0.1 });
    const eyebrow = hero.querySelector('.eyebrow');
    if (eyebrow) tl.fromTo(eyebrow, { opacity: 0, y: 8 }, { opacity: 1, y: 0, duration: 0.45 }, 0);
    if (lines.length) tl.to(lines, { yPercent: 0, duration: 0.7, stagger: 0.08 }, 0.05);

    const copy = $$('.lead, .hero-actions, .hero-register', hero);
    if (copy.length) tl.fromTo(copy, { opacity: 0, y: 16 }, { opacity: 1, y: 0, duration: 0.55, stagger: 0.07 }, 0.35);

    const visual = hero.querySelector('.hero-visual');
    if (visual) {
      tl.fromTo(visual, { opacity: 0 }, { opacity: 1, duration: 0.5, ease: 'power2.out' }, 0.2);
      const art = visual.querySelector('.hv-art');
      if (art) tl.fromTo(art, { y: 24, scale: 0.97 }, { y: 0, scale: 1, duration: 0.7 }, 0.2);
      const rows = $$('.spec-sheet > div', visual);
      if (rows.length) tl.fromTo(rows, { opacity: 0, y: 8 }, { opacity: 1, y: 0, duration: 0.4, stagger: 0.05 }, 0.5);
    }

    // Маршрут опрыскивания прорисовывается под дроном — «авторский» момент страницы
    const route = hero.querySelector('.route-draw');
    if (route) tl.fromTo(route, { strokeDashoffset: 1 }, { strokeDashoffset: 0, duration: 1.4, ease: 'power2.inOut' }, 0.3);
  }

  /* ---------- Внутренние страницы сайта: шапка страницы каскадом ---------- */
  const pageTop = $$('.roi-top > *');
  if (pageTop.length) {
    gsap.fromTo(pageTop, { opacity: 0, y: 16 }, { opacity: 1, y: 0, duration: 0.55, stagger: 0.07, delay: 0.05, clearProps: 'transform' });
  }

  /* ---------- Вход / регистрация и 404: маршрут на поле + содержимое ---------- */
  const authMain = $$('.login-brand, .auth-main > *');
  if (authMain.length) {
    gsap.fromTo(authMain, { opacity: 0, y: 16 }, { opacity: 1, y: 0, duration: 0.5, stagger: 0.06, delay: 0.05, clearProps: 'transform' });
    // Строки выбора кабинета идут списком
    const cards = $$('.portal-card');
    if (cards.length) gsap.from(cards, { opacity: 0, y: 12, duration: 0.45, stagger: 0.06, delay: 0.2, clearProps: 'all' });
  }
  $$('.auth-field .route-draw, .nf-field .route-draw').forEach((path) => {
    gsap.fromTo(path, { strokeDashoffset: 1 }, { strokeDashoffset: 0, duration: 1.4, ease: 'power2.inOut', delay: 0.2 });
  });

  /* ---------- Цифры: count-up до исходного текста ---------- */
  const NBSP = String.fromCharCode(160);
  const fmt = (n) => String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, NBSP);
  function countUp(el) {
    const text = el.textContent;
    const m = text.match(/\d[\d\s]*/); // \s в JS включает и неразрывный пробел
    if (!m) return;
    const target = parseInt(m[0].replace(/\s/g, ''), 10);
    const before = text.slice(0, m.index);
    const after = text.slice(m.index + m[0].length);
    const sep = /\s$/.test(m[0]) ? m[0].match(/\s+$/)[0] : '';
    const state = { v: 0 };
    gsap.to(state, {
      v: target,
      duration: target > 100 ? 1.1 : 0.8,
      ease: 'power2.out',
      onUpdate: () => { el.textContent = before + fmt(state.v) + sep + after; },
      onComplete: () => { el.textContent = text; },
    });
  }

  /* ---------- Появление при входе в вьюпорт, один раз ---------- */
  const reveal = $$('[data-reveal]');
  if (reveal.length) {
    if (ScrollTrigger) {
      gsap.set(reveal, { opacity: 0, y: 20 });
      ScrollTrigger.batch(reveal, {
        start: 'top 88%',
        once: true,
        onEnter: (batch) => {
          gsap.to(batch, { opacity: 1, y: 0, duration: 0.6, stagger: 0.06, overwrite: true, clearProps: 'transform' });
          batch.forEach((el) => {
            const num = el.querySelector('[data-count]');
            if (num) countUp(num);
          });
        },
      });
    } else {
      gsap.to(reveal, { opacity: 1, duration: 0.4 });
    }
  }

  /* ---------- Кабинеты: только лёгкое появление контента ---------- */
  const cabinet = $$('main.emain > *');
  if (cabinet.length) {
    gsap.fromTo(cabinet, { opacity: 0, y: 8 }, {
      opacity: 1, y: 0, duration: 0.4, ease: 'power2.out',
      stagger: { each: 0.04, amount: Math.min(0.24, cabinet.length * 0.04) },
      clearProps: 'transform',
    });
  }

  // Картинки догружаются — пересчитываем точки срабатывания
  if (ScrollTrigger) window.addEventListener('load', () => ScrollTrigger.refresh());
})();
