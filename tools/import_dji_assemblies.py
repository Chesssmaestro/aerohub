"""Извлекает узлы сборки (эксплод-схемы) DJI T50/T55/T70P/T100 из файлов
"...Aircraft_Material information...xlsx" внутри исходных zip-архивов.

Каждый лист файла — один узел (модуль): список деталей (BOM) + фото узла (embedded image).
Разные модели называют похожие узлы по-разному (англ./кит.) — здесь они сводятся
к общим русским названиям (см. NODE_RULES), поэтому «Передняя рама» на сайте одна
что для T100, что для T55, просто с разным составом деталей и фото.

Артикулы в этих файлах даны БЕЗ версии (сам DJI это пишет прямо в файле — "物料编码不含
版本号" / "material number does not contain the version number"), поэтому сопоставление
с data/parts.json идёт по артикулу без версии. Для узлов без совпадения создаётся
новая позиция каталога (как в tools/import_dji_catalogs.py — цена/наличие уточняются
складом).

Результат:
  - data/parts.json — дополняется новыми позициями (если какой-то артикул узла
    не найден в каталоге)
  - data/part_assemblies.json — список узлов: {model, name, image, articles}
    (артикулы без версии, порядок = порядок деталей на схеме)
  - app/static/img/parts/{model}/{node}.jpg — фото узла

Импорт в базу — import_assemblies() в app/seed.py, при каждом старте приложения.

Запуск:  .venv\\Scripts\\pip install openpyxl
         .venv\\Scripts\\python tools\\import_dji_assemblies.py
"""

import html
import io
import json
import re
import sys
import zipfile
from pathlib import Path

import openpyxl
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent.parent
PARTS_JSON = BASE_DIR / 'data' / 'parts.json'
ASSEMBLIES_JSON = BASE_DIR / 'data' / 'part_assemblies.json'
IMG_DIR = BASE_DIR / 'app' / 'static' / 'img' / 'parts'

sys.path.insert(0, str(BASE_DIR))
from tools.import_dji_catalogs import GROUPS, TYPES, classify  # noqa: E402

CATALOGS = {
    'T100': ('DJI T100.zip', 'DJI T100/【EN】T100 Aircraft_Material information 20260417.xlsx'),
    'T50': ('DJI T50.zip', 'DJI T50/T50_Aircraft_Material_information_compilation_2023040327_5.xlsx'),
    'T55': ('DJI T55.zip', 'DJI T55/【EN】T55 Aircraft_Material information.xlsx'),
    'T70': ('DJI T70.zip', 'DJI T70/【EN】T70P Aircraft_Material information 20260417.xlsx'),
}

ARTICLE_RE = re.compile(r'^[A-Za-z]{2}\.[A-Za-z]{2}\.')

# (проверка, канонич. русское имя узла) — первое совпадение побеждает
NODE_RULES = [
    (lambda n, low: '目录' in n or 'list' in low, None),
    (lambda n, low: 'middle frame&rear frame' in low.replace(' & ', '&').replace(' &', '&'),
     'Средняя и задняя рама'),
    (lambda n, low: '前壳前盖组件' in n, 'Передний корпус'),
    (lambda n, low: '前框' in n or 'front frame' in low, 'Передняя рама'),
    (lambda n, low: '后框' in n, 'Задняя рама'),
    (lambda n, low: '中框' in n or 'middle frame' in low, 'Средняя рама'),
    (lambda n, low: '脚架' in n or 'landing gear' in low or 'lower support' in low, 'Шасси (стойки)'),
    (lambda n, low: '喷杆' in n or 'spray lance' in low, 'Распылительная штанга'),
    (lambda n, low: 'frame connector' in low, 'Соединитель рамы'),
    (lambda n, low: '大分线板' in n or 'distribution board' in low or 'cable distribution' in low,
     'Распределительная плата'),
    (lambda n, low: '水箱' in n or 'spray tank' in low, 'Бак'),
    (lambda n, low: '叶轮泵' in n or 'impeller pump' in low, 'Насос (крыльчатка)'),
    (lambda n, low: '流量计' in n or 'flow meter' in low, 'Расходомер'),
    (lambda n, low: 'm1m3 aircraft arm' in low, 'Луч M1/M3'),
    (lambda n, low: 'm1机臂' in low or 'm1 aircraft arm' in low, 'Луч M1'),
    (lambda n, low: 'm3机臂' in low or 'm3 aircraft arm' in low, 'Луч M3'),
    (lambda n, low: 'large aircraft arm' in low, 'Луч (большой)'),
    (lambda n, low: 'aircraft arm' in low, 'Луч'),
    (lambda n, low: '线材' in n, 'Кабели'),
    (lambda n, low: 'motor' in low, 'Мотор'),
    (lambda n, low: '桨叶' in n or 'propeller' in low, 'Пропеллер'),
]

NODE_ORDER = ['Передний корпус', 'Передняя рама', 'Средняя рама', 'Средняя и задняя рама',
              'Задняя рама', 'Соединитель рамы', 'Распределительная плата', 'Бак',
              'Насос (крыльчатка)', 'Расходомер', 'Распылительная штанга', 'Шасси (стойки)',
              'Луч', 'Луч M1', 'Луч M3', 'Луч M1/M3', 'Луч (большой)', 'Мотор',
              'Пропеллер', 'Кабели']


def classify_node(raw_name: str) -> str | None:
    low = raw_name.lower()
    for check, canonical in NODE_RULES:
        if check(raw_name, low):
            return canonical
    print(f'  ! неизвестный узел (пропущен): {raw_name!r}')
    return None


def slugify(text: str) -> str:
    table = str.maketrans({
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e', 'ж': 'zh',
        'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o',
        'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'h', 'ц': 'c',
        'ч': 'ch', 'ш': 'sh', 'щ': 'sch', 'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu',
        'я': 'ya',
    })
    slug = text.lower().translate(table)
    slug = re.sub(r'[^a-z0-9]+', '-', slug).strip('-')
    return slug or 'node'


def find_header(rows: list[tuple]) -> tuple[int, int] | None:
    for i, row in enumerate(rows):
        for j, v in enumerate(row):
            if isinstance(v, str) and v.strip() == 'No.':
                return i, j
    return None


def parse_sheet(ws) -> list[tuple[str, str]]:
    """→ [(артикул без версии, английское имя), ...] в порядке BOM."""
    rows = list(ws.iter_rows(values_only=True))
    header = find_header(rows)
    if header is None:
        return []
    header_row, col_no = header
    items = []
    for row in rows[header_row + 1:]:
        if col_no + 3 >= len(row):
            continue
        article = row[col_no + 1]
        name_en = row[col_no + 3]
        if not article or not isinstance(article, str) or not ARTICLE_RE.match(article.strip()):
            continue
        items.append((article.strip(), (name_en or '').strip() or article.strip()))
    return items


def sheet_image(zf2: zipfile.ZipFile, workbook_xml: str, wb_rels: dict[str, str],
                sheet_name_to_rid: dict[str, str], sheet_name: str) -> bytes | None:
    rid = sheet_name_to_rid.get(sheet_name)
    if rid is None or rid not in wb_rels:
        return None
    sheet_path = 'xl/' + wb_rels[rid]
    sheet_file = sheet_path.rsplit('/', 1)[-1]
    rels_path = f'xl/worksheets/_rels/{sheet_file}.rels'
    if rels_path not in zf2.namelist():
        return None
    sheet_rels = zf2.read(rels_path).decode('utf-8')
    m = re.search(r'Target="\.\./drawings/([^"]+)"', sheet_rels)
    if not m:
        return None
    drawing_rels_path = f'xl/drawings/_rels/{m.group(1)}.rels'
    if drawing_rels_path not in zf2.namelist():
        return None
    drawing_rels = zf2.read(drawing_rels_path).decode('utf-8')
    m2 = re.search(r'Target="\.\./media/([^"]+)"', drawing_rels)
    if not m2:
        return None
    media_path = f'xl/media/{m2.group(1)}'
    if media_path not in zf2.namelist():
        return None
    return zf2.read(media_path), media_path.rsplit('.', 1)[-1]


def load_workbook_bytes(zip_name: str, inner: str) -> bytes:
    with zipfile.ZipFile(BASE_DIR / zip_name) as zf:
        return zf.read(inner)


def main() -> None:
    existing = json.loads(PARTS_JSON.read_text(encoding='utf-8'))
    stripped_to_article: dict[str, str] = {}
    for p in existing:
        stripped = re.sub(r'\.\d+$', '', p['article'])
        stripped_to_article.setdefault(stripped, p['article'])
    next_id = max(p['external_id'] for p in existing) + 1
    new_parts: list[dict] = []

    assemblies: list[dict] = []
    IMG_DIR.mkdir(parents=True, exist_ok=True)

    for model, (zip_name, inner) in CATALOGS.items():
        print('====', model)
        data = load_workbook_bytes(zip_name, inner)
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)

        wb_xml = zipfile.ZipFile(io.BytesIO(data)).read('xl/workbook.xml').decode('utf-8')
        sheet_name_to_rid = {html.unescape(name): rid for name, rid in
                             re.findall(r'<sheet name="([^"]+)"[^>]*r:id="(rId\d+)"', wb_xml)}
        wb_rels_xml = zipfile.ZipFile(io.BytesIO(data)).read('xl/_rels/workbook.xml.rels').decode('utf-8')
        wb_rels = dict(re.findall(r'Id="(rId\d+)"[^>]*Target="([^"]+)"', wb_rels_xml))
        zf2 = zipfile.ZipFile(io.BytesIO(data))

        # canonical node -> {"articles": {article: name_en}, "image_sheet": raw_sheet_name}
        nodes: dict[str, dict] = {}
        for sheet_name in wb.sheetnames:
            canonical = classify_node(sheet_name)
            if canonical is None:
                continue
            items = parse_sheet(wb[sheet_name])
            if not items:
                continue
            bucket = nodes.setdefault(canonical, {'articles': {}, 'image_sheet': sheet_name})
            for article, name_en in items:
                bucket['articles'].setdefault(article, name_en)
        wb.close()

        model_dir = IMG_DIR / model.lower()
        model_dir.mkdir(parents=True, exist_ok=True)

        ordered_nodes = sorted(nodes.items(),
                               key=lambda kv: NODE_ORDER.index(kv[0]) if kv[0] in NODE_ORDER else 999)
        for position, (node_name, bucket) in enumerate(ordered_nodes):
            image_rel = ''
            found = sheet_image(zf2, wb_xml, wb_rels, sheet_name_to_rid, bucket['image_sheet'])
            if found and found[1].lower() in ('jpg', 'jpeg', 'png', 'gif', 'webp'):
                img_bytes, _ext = found
                fname = f'{slugify(node_name)}.jpg'
                img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
                img.thumbnail((1280, 1280), Image.LANCZOS)
                img.save(model_dir / fname, 'JPEG', quality=78, optimize=True)
                image_rel = f'/static/img/parts/{model.lower()}/{fname}'

            articles = list(bucket['articles'].keys())
            for article, name_en in bucket['articles'].items():
                if article not in stripped_to_article:
                    stripped_to_article[article] = article
                    new_parts.append({
                        'external_id': next_id,
                        'name': name_en,
                        'article': article,
                        'price': 0,
                        'stock': 'Под заказ',
                        'group': classify(name_en, GROUPS, 'Прочие узлы'),
                        'kind': classify(name_en, TYPES, 'Прочее'),
                        'models': [model],
                    })
                    next_id += 1

            assemblies.append({
                'model': model,
                'name': node_name,
                'image': image_rel,
                'position': position,
                'articles': articles,
            })
            print(f'  {node_name}: {len(articles)} дет.{"" if image_rel else "  (без фото)"}')

    if new_parts:
        combined = existing + new_parts
        combined.sort(key=lambda x: x['external_id'])
        PARTS_JSON.write_text(json.dumps(combined, ensure_ascii=False, indent=1), encoding='utf-8')
    ASSEMBLIES_JSON.write_text(json.dumps(assemblies, ensure_ascii=False, indent=1), encoding='utf-8')

    print(f'\nузлов: {len(assemblies)}, новых позиций каталога: {len(new_parts)}')


if __name__ == '__main__':
    main()
