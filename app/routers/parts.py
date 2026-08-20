from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Part, PartRequestItem, ROLE_CLIENT, User
from ..models import Request as LeadRequest
from ..security import get_current_user
from ..templating import templates

router = APIRouter()

PER_PAGE = 24
MODEL_ORDER = ['T10', 'T16', 'T20', 'T20P', 'T25', 'T25P', 'T30', 'T40', 'T50',
               'T70', 'T70P', 'T100', 'J150']


def facet(db: Session, column) -> list[tuple[str, int]]:
    rows = db.execute(select(column, func.count()).group_by(column).order_by(func.count().desc()))
    return [(value, count) for value, count in rows if value]


def model_facet(db: Session) -> list[tuple[str, int]]:
    """Совместимость хранится строкой «T50,T40» — считаем вхождения по каждой модели."""
    counts = []
    for model in MODEL_ORDER:
        count = db.scalar(select(func.count()).select_from(Part).where(
            or_(Part.models == model,
                Part.models.like(f'{model},%'),
                Part.models.like(f'%,{model},%'),
                Part.models.like(f'%,{model}'))))
        if count:
            counts.append((model, count))
    return counts


@router.get('/parts')
def parts_list(request: Request, q: str = '', model: str = '', group: str = '', kind: str = '',
               stock: str = '', page: int = 1, db: Session = Depends(get_db),
               user: User | None = Depends(get_current_user)):
    query = select(Part)
    if q.strip():
        needle = f'%{q.strip()}%'
        query = query.where(or_(Part.name.ilike(needle), Part.article.ilike(needle)))
    if model:
        query = query.where(or_(Part.models == model,
                                Part.models.like(f'{model},%'),
                                Part.models.like(f'%,{model},%'),
                                Part.models.like(f'%,{model}')))
    if group:
        query = query.where(Part.group == group)
    if kind:
        query = query.where(Part.kind == kind)
    if stock == 'in':
        query = query.where(Part.stock.notin_(['Под заказ', 'Нет', 'Снят с продажи']))

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    pages = max(1, -(-total // PER_PAGE))
    page = max(1, min(page, pages))
    items = list(db.scalars(query.order_by(Part.name).offset((page - 1) * PER_PAGE).limit(PER_PAGE)))

    return templates.TemplateResponse(request, 'public/parts.html', {
        'user': user, 'active': 'parts', 'items': items, 'total': total,
        'page': page, 'pages': pages,
        'q': q, 'model': model, 'group': group, 'kind': kind, 'stock': stock,
        'groups': facet(db, Part.group), 'kinds': facet(db, Part.kind),
        'models': model_facet(db),
        'catalog_size': db.scalar(select(func.count()).select_from(Part)) or 0,
    })


@router.get('/parts/{part_id}')
def part_card(part_id: int, request: Request, sent: str = '', db: Session = Depends(get_db),
              user: User | None = Depends(get_current_user)):
    part = db.get(Part, part_id)
    if part is None:
        return RedirectResponse('/parts', status_code=303)
    similar = list(db.scalars(select(Part).where(Part.group == part.group, Part.id != part.id)
                              .order_by(Part.price).limit(6)))
    return templates.TemplateResponse(request, 'public/part.html', {
        'user': user, 'active': 'parts', 'part': part, 'similar': similar, 'sent': bool(sent),
    })


@router.post('/parts/{part_id}/request')
def request_part(part_id: int, qty: int = Form(1), comment: str = Form(''),
                 db: Session = Depends(get_db), user: User | None = Depends(get_current_user)):
    """Запрос КП на запчасть — только из-под аккаунта, как и остальные заявки."""
    part = db.get(Part, part_id)
    if part is None:
        return RedirectResponse('/parts', status_code=303)
    if user is None:
        return RedirectResponse(f'/login?next=/parts/{part_id}', status_code=303)

    qty = max(1, min(qty, 999))
    lead = LeadRequest(
        name=user.full_name, phone=user.phone, email=user.email,
        farm=user.company.name if user.company else '',
        comment=f'Запчасть {part.article} — {part.name}, {qty} шт. '
                f'на сумму {int(part.price * qty)} ₽.'
                + (f' {comment.strip()}' if comment.strip() else ''),
        source='Запрос по запчасти',
        user_id=user.id,
    )
    db.add(lead)
    db.flush()
    db.add(PartRequestItem(request_id=lead.id, part_id=part.id, qty=qty))
    db.commit()
    return RedirectResponse(f'/parts/{part_id}?sent=1', status_code=303)
