"""Обучение операторов: потоки курса, форматы и переходы статуса записи."""

from datetime import date, datetime, timedelta

from .models import Training
from .templating import RU_MONTHS_GEN

# Курс — два дня подряд, вторник и среда; записываемся не раньше чем за неделю
FORMATS = [
    {'key': 'center', 'name': 'Учебный центр АЭРОХАБ, Самара',
     'note': 'Полигон, тренажёр и техника центра — подходит, если своя машина ещё в пути.'},
    {'key': 'field', 'name': 'Выезд на поле хозяйства',
     'note': 'Инструктор приезжает к вам, практика на вашей технике и ваших полях.'},
]
MAX_OPERATORS = 6

STEPS = [
    ('requested', 'Запись', 'Выберите поток и впишите операторов'),
    ('scheduled', 'Подтверждение', 'Учебный центр подтверждает дату и место'),
    ('course', 'Курс', 'Два дня: теория и практика'),
    ('done', 'Допуск', 'Результат — в цифровом паспорте техники'),
]


def _label(start: date) -> str:
    end = start + timedelta(days=1)
    if start.month == end.month:
        return f'{start.day}–{end.day} {RU_MONTHS_GEN[start.month - 1]}'
    return f'{start.day} {RU_MONTHS_GEN[start.month - 1]} – {end.day} {RU_MONTHS_GEN[end.month - 1]}'


def upcoming_slots(count: int = 4, today: date | None = None) -> list[dict]:
    """Ближайшие потоки: вторник–среда, начиная через неделю."""
    day = (today or date.today()) + timedelta(days=7)
    day += timedelta(days=(1 - day.weekday()) % 7)  # ближайший вторник
    return [{'key': (day + timedelta(weeks=i)).isoformat(), 'label': _label(day + timedelta(weeks=i))}
            for i in range(count)]


def step_index(training: Training | None) -> int:
    """Номер текущего шага для полосы «Запись → Подтверждение → Курс → Допуск»."""
    state = training.state if training else 'not_planned'
    return {'not_planned': 0, 'requested': 1, 'scheduled': 2, 'done': 4}.get(state, 0)


def book(training: Training, slot_label: str, format_name: str, operators: list[str], note: str) -> None:
    names = [n.strip()[:80] for n in operators if n.strip()][:MAX_OPERATORS]
    training.date_label = slot_label
    training.format = format_name
    training.operators = '\n'.join(names)
    training.participants = len(names)
    training.note = note.strip()[:1000]
    training.status = 'requested'
    training.confirmed = False
    training.confirmed_at = Noneч


def schedule(training: Training) -> None:
    training.status = 'scheduled'
    training.confirmed = True
    training.confirmed_at = datetime.now() 


def complete(training: Training) -> None:
    training.status = 'done'
    training.done_at = datetime.now()
