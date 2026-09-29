"""Уведомления в шапке кабинета: то, что сейчас ждёт действия пользователя.

Список собирается на каждом запросе из текущего состояния — отдельного хранилища нет:
как только дело сделано (чек приложен, заявка принята), пункт исчезает сам.
Каждый пункт — {'title', 'note', 'href', 'tag'}; шаблон показывает первые несколько.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Deal, DealerOrder, Request as LeadRequest
from .orders import stage_info


def for_client(awaiting: list[Deal]) -> list[dict]:
    return [{
        'title': f'Заказ №{d.number} · {d.product}',
        'note': stage_info(d)['client'],
        'href': f'/cabinet/orders/{d.id}',
        'tag': stage_info(d)['title'],
    } for d in awaiting]


def for_dealer(orders: list[DealerOrder]) -> list[dict]:
    return [{
        'title': f'Оптовая заявка · {o.model} × {o.qty}',
        'note': 'Ждёт подтверждения менеджером продаж — резерв появится после согласования.',
        'href': '/dealer/orders',
        'tag': o.status,
    } for o in orders if o.status == 'Новая заявка']


def for_staff(db: Session, can_view_requests: bool, can_view_orders: bool) -> list[dict]:
    items = []
    if can_view_orders:
        for d in db.scalars(select(Deal).order_by(Deal.id.desc())):
            info = stage_info(d)
            if d.training is not None and d.training.state == 'requested':
                items.append({
                    'title': f'Обучение по заказу №{d.number}',
                    'note': f'Клиент записал операторов на {d.training.date_label} — подтвердите запись.',
                    'href': f'/staff/orders/{d.id}',
                    'tag': 'Обучение',
                })
            if info['actor'] == 'staff':
                items.append({
                    'title': f'Заказ №{d.number} · {d.product}',
                    'note': info['staff'],
                    'href': f'/staff/orders/{d.id}',
                    'tag': info['title'],
                })
    if can_view_requests:
        for r in db.scalars(select(LeadRequest).where(LeadRequest.status == 'Новая')
                            .order_by(LeadRequest.id.desc())):
            items.append({
                'title': f'{r.source} · {r.name}',
                'note': (r.comment[:110] + '…') if len(r.comment) > 110 else (r.comment or 'Без комментария'),
                'href': '/staff/requests',
                'tag': 'Новая',
            })
    return items
