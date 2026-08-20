"""Сбор каталога запчастей в data/parts.json.

Источник — публичный каталог agi-systems.ru. Данные (артикулы, цены, наличие) чужие
и в рабочем портале должны быть заменены собственным прайсом.

Запуск:  .venv\\Scripts\\python tools\\fetch_parts.py [число_страниц]
"""

import html
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

BASE = 'https://agi-systems.ru/catalog/parts/'
OUT = Path(__file__).resolve().parent.parent / 'data' / 'parts.json'
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; AEROHUB catalog import)'}

CARD_RE = re.compile(
    r'href="/catalog/parts/(?P<id>\d+)/"[^>]*js-notice-block__title[^>]*>\s*<span>(?P<name>.*?)</span>',
    re.S)
STOCK_RE = re.compile(r'data-id="{id}"[^>]*>.*?<span class="value[^"]*">(.*?)</span>', re.S)
ART_RE = re.compile(r'data-name="Арт\." data-value="(.*?)"')
PRICE_RE = re.compile(r'data-currency="RUB" data-value="([\d.]+)"')

# Группа узла и тип детали определяются по названию: на странице каталога
# у карточки нет этих полей, а заходить в 2500 карточек ради них избыточно.
GROUPS = [
    ('Опрыскивание', ('распылител', 'форсунк', 'сопло', 'опрыск', 'штанг')),
    ('Насосы и расход', ('насос', 'расходомер', 'помп', 'клапан', 'шланг', 'фитинг', 'трубк')),
    ('Бак и жидкостная система', ('бак', 'крышк бак', 'фильтр', 'уровн')),
    ('Внесение гранул', ('гранул', 'бункер', 'шнек', 'дозатор', 'разбрасыват')),
    ('Лучи и моторы', ('луч', 'мотор', 'двигател', 'esc', 'регулятор оборот')),
    ('Винты и пропеллеры', ('пропеллер', 'лопаст', 'винт возд', 'складн')),
    ('Шасси и рама', ('шасси', 'рама', 'стойк', 'опор', 'корпус', 'кронштейн')),
    ('Аккумуляторы и питание', ('аккумулятор', 'батаре', 'зарядн', 'питани', 'генератор', 'кабель питания')),
    ('Электроника и датчики', ('плат', 'модул', 'датчик', 'радар', 'камер', 'антенн', 'gnss', 'rtk', 'светодиод')),
    ('Пульт управления', ('пульт', 'джойстик', 'экран пульт', 'стик')),
    ('Кабели и разъёмы', ('кабель', 'разъём', 'разъем', 'шлейф', 'провод', 'коннектор')),
    ('Крепёж и уплотнения', ('болт', 'винт', 'гайк', 'шайб', 'саморез', 'заклёпк', 'уплотнит',
                             'прокладк', 'кольцо', 'сальник', 'хомут', 'стопор')),
]

TYPES = [
    ('Крепёж', ('болт', 'винт ', 'гайк', 'шайб', 'саморез', 'заклёпк', 'штифт', 'хомут')),
    ('Уплотнения', ('уплотнит', 'прокладк', 'кольцо', 'сальник', 'манжет')),
    ('Кабели и разъёмы', ('кабель', 'разъём', 'разъем', 'шлейф', 'провод')),
    ('Платы и модули', ('плат', 'модул', 'контроллер', 'блок управления')),
    ('Датчики', ('датчик', 'радар', 'камер', 'сенсор')),
    ('Насосы', ('насос', 'помп')),
    ('Распылители', ('распылител', 'форсунк', 'сопло')),
    ('Пропеллеры', ('пропеллер', 'лопаст')),
    ('Моторы', ('мотор', 'двигател')),
    ('Корпусные детали', ('корпус', 'крышк', 'панел', 'кожух', 'заглушк')),
    ('Баки и ёмкости', ('бак', 'бункер', 'ёмкост')),
    ('Шланги и фитинги', ('шланг', 'фитинг', 'трубк', 'штуцер')),
    ('Аккумуляторы', ('аккумулятор', 'батаре')),
    ('Антенны', ('антенн',)),
]

MODEL_RE = re.compile(r'\bT\d{2,3}P?\b|\bJ150\b')


def classify(name: str, table: list[tuple[str, tuple[str, ...]]], default: str) -> str:
    low = name.lower()
    for title, keys in table:
        if any(k in low for k in keys):
            return title
    return default


def compat_models(name: str) -> list[str]:
    """Совместимость вытаскиваем из названия: «... для DJI Agras T50/T40/T25»."""
    tail = name.split('для', 1)[1] if 'для' in name else ''
    return sorted(set(MODEL_RE.findall(tail)), key=lambda m: (len(m), m))


def fetch(page: int) -> str:
    url = BASE if page == 1 else f'{BASE}?PAGEN_1={page}'
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode('utf-8', 'replace')


def parse(page_html: str) -> list[dict]:
    items = []
    matches = list(CARD_RE.finditer(page_html))
    for i, m in enumerate(matches):
        chunk = page_html[m.end():matches[i + 1].start() if i + 1 < len(matches) else m.end() + 6000]
        name = html.unescape(re.sub(r'<[^>]+>', '', m.group('name'))).strip()
        article = ART_RE.search(chunk)
        price = PRICE_RE.search(chunk)
        stock = STOCK_RE.pattern.replace('{id}', m.group('id'))
        stock_match = re.search(stock, page_html[max(0, m.start() - 3000):m.end() + 3000], re.S)
        if not article or not price:
            continue
        items.append({
            'external_id': int(m.group('id')),
            'name': name,
            'article': article.group(1).strip(),
            'price': float(price.group(1)),
            'stock': html.unescape(stock_match.group(1)).strip() if stock_match else 'Под заказ',
            'group': classify(name, GROUPS, 'Прочие узлы'),
            'kind': classify(name, TYPES, 'Прочее'),
            'models': compat_models(name),
        })
    return items


def main() -> None:
    pages = int(sys.argv[1]) if len(sys.argv) > 1 else 43
    seen: dict[int, dict] = {}
    for page in range(1, pages + 1):
        try:
            items = parse(fetch(page))
        except Exception as exc:  # страница может не открыться — продолжаем со следующей
            print(f'страница {page}: ошибка {exc}')
            continue
        for item in items:
            seen[item['external_id']] = item
        print(f'страница {page}: +{len(items)}, всего {len(seen)}')
        time.sleep(0.4)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    data = sorted(seen.values(), key=lambda x: x['external_id'])
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'сохранено {len(data)} позиций в {OUT}')


if __name__ == '__main__':
    main()
