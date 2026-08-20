from fastapi.templating import Jinja2Templates

from .config import BASE_DIR, COMPANY

templates = Jinja2Templates(directory=str(BASE_DIR / 'app' / 'templates'))


def money(value: float | int | None) -> str:
    """1440000 → «1 440 000 ₽»"""
    if value is None:
        return '—'
    return f'{int(round(value)):,}'.replace(',', ' ') + ' ₽'


def number(value: float | int | None, digits: int = 0) -> str:
    if value is None:
        return '—'
    text = f'{value:,.{digits}f}'.replace(',', ' ')
    return text.replace('.', ',')


def mln(value: float | int | None) -> str:
    """6850000 → «6,85 млн ₽»"""
    if value is None:
        return '—'
    return number(value / 1_000_000, 2) + ' млн ₽'


RU_MONTHS_GEN = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа',
                 'сентября', 'октября', 'ноября', 'декабря']


def ru_month_year(value) -> str:
    """datetime → «августа 2026»"""
    if value is None:
        return ''
    return f'{RU_MONTHS_GEN[value.month - 1]} {value.year}'


def ru_date(value) -> str:
    """datetime → «18 августа 2026»"""
    if value is None:
        return ''
    return f'{value.day} {RU_MONTHS_GEN[value.month - 1]} {value.year}'


templates.env.filters['money'] = money
templates.env.filters['ru_month_year'] = ru_month_year
templates.env.filters['ru_date'] = ru_date
templates.env.filters['number'] = number
templates.env.filters['mln'] = mln
templates.env.globals['company'] = COMPANY
