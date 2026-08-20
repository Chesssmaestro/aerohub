from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import ROLE_DEALER, DealerOrder, Lead, User
from ..security import require_role
from ..templating import ru_month_year, templates

router = APIRouter(prefix='/dealer')

NAV = [
    ('overview', 'Обзор'),
    ('orders', 'Оптовые заявки'),
    ('clients', 'Мои клиенты'),
    ('pricing', 'Цены и матрица'),
    ('materials', 'Материалы и обучение'),
]
NAV_TITLES = dict(NAV)

# Уровни партнёрской программы (черновик, требует утверждения руководителем продаж)
LEVELS = [
    {'name': 'Silver', 'volume': 'до 2 ед. / квартал', 'discount': '—'},
    {'name': 'Gold', 'volume': 'от 3 ед. / квартал', 'discount': 'обсуждается'},
    {'name': 'Platinum', 'volume': 'от 6 ед. / квартал', 'discount': 'обсуждается'},
]


def context(request: Request, db: Session, user: User, section: str) -> dict:
    orders = list(db.scalars(select(DealerOrder).where(DealerOrder.company_id == user.company_id)
                             .order_by(DealerOrder.id.desc()))) if user.company_id else []
    leads = list(db.scalars(select(Lead).where(Lead.company_id == user.company_id)
                            .order_by(Lead.id.desc()))) if user.company_id else []
    return {
        'request': request, 'user': user, 'nav': NAV, 'active': section,
        'crumb': NAV_TITLES.get(section, ''), 'orders': orders, 'leads': leads, 'levels': LEVELS,
        'org_name': user.company.name if user.company else user.full_name,
        'org_sub': f'{user.full_name} · поставщик с {ru_month_year(user.created_at)}',
        'level': user.company.dealer_level if user.company else 'Silver',
        'notifications': len([o for o in orders if o.status == 'Новая заявка']),
    }


@router.get('')
def dealer_root(request: Request, db: Session = Depends(get_db),
                user: User = Depends(require_role(ROLE_DEALER))):
    return templates.TemplateResponse(request, 'dealer/overview.html',
                                      context(request, db, user, 'overview'))


@router.get('/{section}')
def dealer_section(section: str, request: Request, db: Session = Depends(get_db),
                   user: User = Depends(require_role(ROLE_DEALER))):
    if section not in NAV_TITLES:
        return RedirectResponse('/dealer', status_code=303)
    return templates.TemplateResponse(request, f'dealer/{section}.html',
                                      context(request, db, user, section))


@router.post('/orders')
def create_order(request: Request, model: str = Form(...), qty: int = Form(1),
                 comment: str = Form(''), db: Session = Depends(get_db),
                 user: User = Depends(require_role(ROLE_DEALER))):
    db.add(DealerOrder(company_id=user.company_id, model=model.strip(), qty=max(1, qty),
                       comment=comment.strip(), status='Новая заявка'))
    db.commit()
    return RedirectResponse('/dealer/orders', status_code=303)


@router.post('/clients')
def create_lead(request: Request, name: str = Form(...), stage: str = Form('Новый лид'),
                contact: str = Form(''), note: str = Form(''), db: Session = Depends(get_db),
                user: User = Depends(require_role(ROLE_DEALER))):
    db.add(Lead(company_id=user.company_id, name=name.strip(), stage=stage,
                contact=contact.strip(), note=note.strip()))
    db.commit()
    return RedirectResponse('/dealer/clients', status_code=303)
