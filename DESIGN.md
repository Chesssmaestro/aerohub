---
name: АЭРОХАБ
description: Портал сделки, поставки и эксплуатации агродронов DJI Agras — публичный сайт и три кабинета
colors:
  graphite-night: "#1B1D20"
  panel: "#232629"
  panel-raised: "#2B2E32"
  hairline: "#2A2A30"
  hairline-bright: "#3B3B43"
  paper: "#F2F2F2"
  ash: "#A6A6A6"
  ash-dim: "#71717A"
  field-gold: "#D4A452"
  field-gold-soft: "#DCB578"
  field-gold-deep: "#8C6C3C"
  status-ok: "#6FBF73"
  status-warn: "#D8A93F"
  status-bad: "#D4665F"
  status-info: "#7FA6D8"
typography:
  display:
    fontFamily: "Unbounded, sans-serif"
    fontSize: "clamp(2.5rem, 1.25rem + 4.2vw, 5.5rem)"
    fontWeight: 600
    lineHeight: 0.98
    letterSpacing: "-0.035em"
  headline:
    fontFamily: "Unbounded, sans-serif"
    fontSize: "clamp(1.875rem, 1.35rem + 1.5vw, 2.75rem)"
    fontWeight: 600
    lineHeight: 1.12
    letterSpacing: "-0.025em"
  title:
    fontFamily: "Unbounded, sans-serif"
    fontSize: "1.375rem"
    fontWeight: 500
    lineHeight: 1.25
    letterSpacing: "-0.01em"
  lead:
    fontFamily: "Golos Text, sans-serif"
    fontSize: "1.125rem"
    fontWeight: 400
    lineHeight: 1.6
  body:
    fontFamily: "Golos Text, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.6
  body-dense:
    fontFamily: "Golos Text, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.55
  figure:
    fontFamily: "Unbounded, sans-serif"
    fontSize: "clamp(2rem, 1.5rem + 1.6vw, 3.25rem)"
    fontWeight: 500
    lineHeight: 1
    letterSpacing: "-0.03em"
    fontFeature: "tnum"
  label:
    fontFamily: "Golos Text, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 500
    letterSpacing: "0.14em"
rounded:
  base: "2px"
spacing:
  "1": "4px"
  "2": "8px"
  "3": "12px"
  "4": "16px"
  "5": "24px"
  "6": "32px"
  "7": "48px"
  "8": "64px"
  "9": "96px"
  "10": "128px"
components:
  button-primary:
    backgroundColor: "{colors.field-gold}"
    textColor: "{colors.graphite-night}"
    rounded: "{rounded.base}"
    padding: "13px 22px"
  button-primary-hover:
    backgroundColor: "{colors.field-gold-soft}"
  button-outline:
    textColor: "{colors.field-gold}"
    rounded: "{rounded.base}"
    padding: "13px 22px"
  button-ghost:
    textColor: "{colors.ash}"
    rounded: "{rounded.base}"
    padding: "13px 22px"
  input:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.paper}"
    rounded: "{rounded.base}"
    padding: "12px 14px"
  card:
    backgroundColor: "{colors.panel}"
    padding: "24px"
  status-chip:
    typography: "{typography.label}"
    rounded: "{rounded.base}"
    padding: "4px 9px"
---

# Design System: АЭРОХАБ

## Overview

**Creative North Star: «Полевой протокол»**

Портал выглядит как рабочий документ агроинженера: тёмный графит, тонкие линии разметки, моноширинные показания и одна оранжевая метка там, где решение или деньги. Красота — в точности, а не в декоре. Мотив бренда — поле: сетка участков и «змейка» маршрута опрыскивания. Он заменяет декоративные свечения и появляется только там, где уместна карта: hero, экран входа, 404, фон CTA.

Публичный сайт (режим Persuade) говорит крупно и уверенно: огромный заголовок, одна главная кнопка, секции разной композиции. Кабинеты (режим Operate) плотные и спокойные: те же токены, меньше кегль, никакого театра.

Отвергнуто явно: radial-свечения, glow-тени, градиентные панели, glassmorphism, фиолетово-синие градиенты, капс во всех заголовках, одинаковые сетки карточек на каждой секции.

**Key Characteristics:**
- Сетки «волосяной линией» (`gap:1px` на фоне `--line`) — приборный вид таблиц, KPI и досок сравнения.
- Радиус 2px везде; скругления не растут.
- Акцент — ≤10% экрана: главная кнопка, цена, текущий этап, маршрут.
- Данные — табличными цифрами основного шрифта (Golos Text).

## Colors

Графит и бумага, с одним ярким оранжевым акцентом и зелёной вершиной знака.

### Primary
- **Оранжевый АЭРОХАБ** (#FF6A1A): главная кнопка, цены, текущий этап, активный пункт меню, маршрут на поле. Hover — #FF7D38; рамки outline — #B84E15.
- **Зелёный знака** (#5FAE47): вершина шеврона в логотипе, полевые данные.

### Neutral
- **Графитовая ночь** (#0A0B0D): фон страницы, шапки.
- **Панель** (#14161A) / **Панель выше** (#1A1D22): карточки, сайдбар, активные строки.
- **Волосяная линия** (#23262D) / **Яркая линия** (#34383F): разделители, рамки, сетка поля.
- **Бумага** (#F2F3F5): основной текст и заголовки.
- **Пепел** (#8B92A0): весь вторичный читаемый текст.
- **Тусклый пепел** (#5B6270): только плейсхолдеры, разделители-символы, неактивное. 3.7:1 — для текста не годится.

### Status
- ok #4ADE80 · warn #FBBF24 · bad #F87171 · info #60A5FA — только для статусов, никогда для характеристик.

### Named Rules
**Правило читаемости.** Любой текст, который нужно прочитать, — `--text` или `--text-muted`. `--text-dim` для текста запрещён (AA).
**Правило одной метки.** Оранжевый отмечает решение, деньги или «где мы сейчас». Декоративного оранжевого нет.

## Typography

**Display:** Unbounded (400–700)
**Body / Data:** Golos Text (400–700)

**Character:** гротеск с инженерными засечками-деталями в крупном размере; моно — голос приборов.

### Hierarchy
Токены в `:root` app.css: `--fs-label` 12 · `--fs-xs` 13 · `--fs-sm` 14 · `--fs-body` 16 · `--fs-lead` 18 · `--fs-h3` 22 · `--fs-h2` 30→44 · `--fs-h1` 40→88 · `--fs-num` 32→52.
- **Display** (600, `--fs-h1`, 0.98, −0.035em): hero, 404. Обычный регистр.
- **Page title** (600, 32→60px, 1.02): шапки внутренних страниц `.roi-top h1`.
- **Headline** (600, `--fs-h2`, 1.12): заголовки секций сайта.
- **Cabinet title** (600, 26→36px): `.page-head h1`, `.role-head h1`.
- **Title** (500, `--fs-h3`): строки, узлы, названия моделей.
- **Body** (400, 16px, 1.6–1.7, ≤60–62ch) на сайте; **Body dense** 14px в кабинетах.
- **Label** (Mono 500, 12px, 0.1–0.14em, КАПС): eyebrow, метки карточек, заголовки таблиц, статусы.

### Named Rules
**Правило капса.** Капс — только у моно-меток (eyebrow, `.card h4`, `th`, `.status-chip`, ярлык роли). Заголовки h1–h3 — обычный регистр.
**Правило 12px.** Ничего мельче 12px на экране, включая подписи SVG-графиков.
**Цифры — табличные.** `font-variant-numeric: tabular-nums` у цен, KPI, count-up.

## Layout

Контейнер сайта `.pub-wrap`: max 1600px, поле `--gutter` = clamp(16px, 3vw, 40px). Шкала отступов — шаг 4px (`--sp-1`…`--sp-10`).

Ритм сайта намеренно неровный: hero 96/64, «Обработка» 128 сверху, остальные секции 96/64. Каждая секция главной имеет свою композицию: сплит hero, линейка цифр, тезис + строки, доска сравнения, линия данных, CTA на линии. Не повторять одну сетку карточек дважды подряд.

Кабинет: шапка 60px, сайдбар 240/272px (sticky), контент — полная ширина с полями 32px. Брейкпоинты: 1180 (карточки 4→2), 900 (колонки → одна, сайдбар по кнопке), 820 (мобильная шапка), 700, 520. На 375px нет горизонтального скролла; таблицы прокручиваются внутри `.table-wrap`, линейка моделей — лента со scroll-snap.

## Elevation & Depth

Плоская система. Глубина — тоном (`--panel` → `--panel-2`) и линиями. Единственная тень — `drop-shadow` под фото дронов (реальный объект над полем). Никаких glow, цветных ореолов и `box-shadow` с нулевым смещением.

**Правило плоскости.** Состояние показывают тон, линия или оранжевая черта — не тень.

## Shapes

Радиус `--radius: 2px` у всех кнопок, полей, чипов. Разделители — 1px. Акцентные черты — 2px (текущий шаг, подчёркивание строки при hover). Знак бренда — скошенный параллелограмм (`skewX(-24deg)`) у заголовков блоков и пунктов правил. Цветная полоса слева шире 1px запрещена: предупреждения — тонированная рамка по периметру.

## Components

- **Кнопки:** `.btn-primary` (оранжевый), `.btn-outline`, `.btn-ghost`; `.btn-lg` для hero/CTA. Hover 160ms по `background-color / border-color / color`, нажатие `translateY(1px)`. На сайте одна главная кнопка на экран; вторичное действие — `.link-arrow` (текст + стрелка).
- **Ссылки:** `.link-accent` — подчёркивание проявляется при hover (offset 4px).
- **Шапка сайта:** активный пункт — оранжевая линия `scaleX`. Мобильное меню — панель под шапкой, opacity + translateY 240ms, пункты с задержкой 30ms.
- **Поля:** 16px, фон `--panel`, рамка `--line-bright`; фокус — оранжевая рамка + outline 2px. Метки связаны с полями через `for`/`id`.
- **Карточки кабинета:** сетка волосяной линией; метка `h4` — моно 12px капсом `--text-muted`. `.doc-row` переносит статус на новую строку, а не сжимает сумму.
- **Строки-списки** (`.work-row`, `.portal-card`): подчёркивание акцентом слева направо при hover (transform, 600ms).
- **Статусы:** `.status-chip` / `.doc-status` — моно 12px, цвет только из статусной палитры.

## Motion

Библиотеки: GSAP 3.15.0 + ScrollTrigger (cdnjs), Lenis 1.3.26 (jsdelivr); весь код — `app/static/js/motion.js`.

- **Токены:** `--dur-fast` 160ms (hover), `--dur-base` 240ms (состояния, меню), `--dur-slow` 600ms (появление); `--ease-out` cubic-bezier(.16,1,.3,1) ≈ power3.out. Без bounce/elastic.
- **Анимируются только** transform и opacity (плюс `stroke-dashoffset` маски маршрута). Никаких width/height/top/margin.
- **Авторский момент** — hero: заголовок по строкам (маски, stagger 80ms), лид и кнопки каскадом, дрон проявляется, маршрут опрыскивания прорисовывается под ним (1.4s).
- **Появление** `[data-reveal]`: fade + 20px, stagger 60ms, один раз (`ScrollTrigger.batch`, once). Цифры `[data-count]` считаются вверх и возвращают исходный текст.
- **Lenis** — только на страницах с `.pubnav`. В кабинетах скролл нативный; там только появление контента за 400ms.
- **Прогрессивное улучшение:** класс `js-motion` ставится в `<head>` и снимается, если библиотеки или `motion.js` не загрузились. Без JS и при `prefers-reduced-motion: reduce` весь контент виден сразу, Lenis не создаётся, tween'ов нет; CSS-переходы сведены к 0.01ms.
- Анимации не перехватывают `input`/`click` — `roi.js`, `configurator.js`, `nav.js` работают как прежде.

## Do's and Don'ts

**Do**
- Держать один главный CTA на экран; второе действие — текстовой ссылкой.
- Менять композицию от секции к секции; повторение — только ради узнавания.
- Использовать мотив поля там, где уместна карта; статично на экране входа, с прорисовкой в hero.
- Проверять 375 / 768 / 1280 / 1600 без горизонтального скролла.

**Don't**
- Не добавлять radial-свечения, glow-тени, градиентные панели, glassmorphism, блобы, курсор-эффекты, parallax.
- Не писать `transition: all`.
- Не набирать заголовки капсом и не ставить eyebrow над каждой секцией.
- Не использовать `--text-dim` для читаемого текста и не опускаться ниже 12px.
- Не включать Lenis, pin-секции и скролл-театр в кабинетах.
