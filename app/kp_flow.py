"""Заявка на КП в один шаг: данные о хозяйстве → заявка в кабинете покупателя.

Контакты (имя, телефон, почту) не спрашиваем — берём из аккаунта.
Если человек ещё не вошёл, заполненная форма ждёт в сессии, пока он войдёт или
зарегистрируется, и затем оформляется сама — без повторного ввода.
"""

from fastapi import Request
from sqlalchemy.orm import Session

from .models import ROLE_CLIENT, Request as LeadRequest, User

DRAFT_KEY = 'kp_draft'
DONE_URL = '/cabinet/orders?kp=1'


def save_draft(request: Request, farm: str, area: str, comment: str) -> None:
    request.session[DRAFT_KEY] = {'farm': farm.strip()[:160], 'area': area.strip()[:40],
                                  'comment': comment.strip()[:2000]}


def has_draft(request: Request) -> bool:
    return DRAFT_KEY in request.session


def create_request(db: Session, user: User, farm: str, area: str, comment: str) -> LeadRequest:
    lead = LeadRequest(
        name=user.full_name, phone=user.phone, email=user.email,
        farm=farm.strip() or (user.company.name if user.company else ''),
        area=area.strip(), comment=comment.strip(),
        source='Форма КП', user_id=user.id,
    )
    db.add(lead)
    db.commit()
    return lead


def finish_draft(request: Request, db: Session, user: User) -> str | None:
    """Оформляет отложенную заявку после входа. Возвращает адрес кабинета или None."""
    draft = request.session.pop(DRAFT_KEY, None)
    if not draft or user.role != ROLE_CLIENT:
        return None
    create_request(db, user, draft.get('farm', ''), draft.get('area', ''), draft.get('comment', ''))
    return DONE_URL
