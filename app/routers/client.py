from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..catalog import MODELS, OPTIONS, PACKAGES
from ..db import get_db
from ..models import ROLE_CLIENT, Deal, Document, Request as LeadRequest, User
from ..orders import (attach_receipt, client_can_upload_receipt, create_order, stage_info,
                      stage_key)
from ..security import require_role
from ..seed import PIPELINE
from ..storage import UploadError, save_upload
from ..templating import ru_month_year, templates

router = APIRouter(prefix='/cabinet')

NAV = [
    ('overview', 'Обзор'),
    ('orders', 'Мои заказы'),
    ('deal', 'Моя сделка'),
    ('config', 'Комплектация'),
    ('docs', 'Документы'),
    ('payment', 'Оплата'),
    ('delivery', 'Поставка'),
    ('training', 'Обучение'),
    ('accounting', 'Учёт и ЭПР'),
    ('ops', 'Обработки'),
    ('service', 'Сервис'),
    ('specialist', 'Специалист'),
]
NAV_TITLES = dict(NAV)


def get_deal(db: Session, user: User) -> Deal | None:
    if not user.company_id:
        return None
    return db.scalar(select(Deal).where(Deal.company_id == user.company_id).order_by(Deal.id.desc()))


def deal_stats(deal: Deal | None) -> dict:
    """Сводка по эксплуатации и оплате для карточек кабинета."""
    if deal is None:
        return {}
    done = [o for o in deal.operations if not o.planned]
    area_total = sum(o.area for o in done if o.unit == 'га')
    paid = sum(p.amount for p in deal.payments if p.paid)
    paid_share = sum(p.share for p in deal.payments if p.paid)
    return {
        'ops_done': len(done),
        'area_total': area_total,
        'avg_per_day': round(area_total / len(done)) if done else 0,
        'season': 2026,
        'paid': paid,
        'paid_share': paid_share,
        'rest_share': 100 - paid_share,
        'rest': sum(p.amount for p in deal.payments if not p.paid),
        'positions': len([c for c in deal.config_items if c.section == 'spec' and c.included]),
    }


def awaiting_client(db: Session, user: User) -> list[Deal]:
    """Заказы, где ход за покупателем — например, ждут чек об оплате."""
    if not user.company_id:
        return []
    deals = db.scalars(select(Deal).where(Deal.company_id == user.company_id).order_by(Deal.id.desc()))
    return [d for d in deals if stage_info(d)['actor'] == 'client']


def context(request: Request, db: Session, user: User, section: str) -> dict:
    deal = get_deal(db, user)
    awaiting = awaiting_client(db, user)
    return {
        'stats': deal_stats(deal),
        'pipeline': PIPELINE,
        'request': request, 'user': user, 'nav': NAV, 'active': section,
        'crumb': NAV_TITLES.get(section, ''), 'deal': deal,
        'awaiting': awaiting,
        'org_name': user.company.name if user.company else user.full_name,
        'org_sub': f'{user.full_name} · клиент с {ru_month_year(user.created_at)}',
        'notifications': len(awaiting),
    }


def render(request: Request, db: Session, user: User, section: str, **extra):
    ctx = context(request, db, user, section)
    ctx.update(extra)
    if section == 'orders':
        # Раздел заказов работает и до появления первой сделки
        deals = list(db.scalars(select(Deal).where(Deal.company_id == user.company_id)
                                .order_by(Deal.id.desc()))) if user.company_id else []
        ctx.update({
            'deals': deals,
            'stage_of': {d.id: stage_info(d) for d in deals},
            'models': MODELS, 'packages': PACKAGES, 'options': OPTIONS,
        })
        return templates.TemplateResponse(request, 'client/orders.html', ctx)
    if ctx['deal'] is None:
        return templates.TemplateResponse(request, 'client/empty.html', ctx)
    return templates.TemplateResponse(request, f'client/{section}.html', ctx)


@router.get('')
def cabinet_root(request: Request, db: Session = Depends(get_db),
                 user: User = Depends(require_role(ROLE_CLIENT))):
    return render(request, db, user, 'overview')


@router.get('/{section}')
def cabinet_section(section: str, request: Request, sent: str = '', placed: str = '',
                    db: Session = Depends(get_db),
                    user: User = Depends(require_role(ROLE_CLIENT))):
    if section not in NAV_TITLES:
        return RedirectResponse('/cabinet', status_code=303)
    return render(request, db, user, section, sent=bool(sent), placed=bool(placed))


@router.post('/orders')
def place_order(request: Request, model: str = Form(...), package: str = Form('pro'),
                options: list[str] = Form(default=[]), city: str = Form(''),
                comment: str = Form(''), db: Session = Depends(get_db),
                user: User = Depends(require_role(ROLE_CLIENT))):
    """Заказ покупателя сразу становится сделкой — она видна сотрудникам в разделе «Заказы»."""
    if not user.company_id:
        return RedirectResponse('/cabinet/orders', status_code=303)
    deal = create_order(db, user, model, package, options, city=city, comment=comment)
    db.add(LeadRequest(name=user.full_name, phone=user.phone, email=user.email,
                       farm=user.company.name if user.company else '',
                       comment=f'Оформлен заказ №{deal.number}: {deal.product} '
                               f'«{deal.package}» на {int(deal.amount):,} ₽'.replace(',', ' ')
                               + (f'. {deal.comment}' if deal.comment else ''),
                       source='Заказ из кабинета', user_id=user.id))
    db.commit()
    return RedirectResponse('/cabinet/orders?placed=1', status_code=303)


def _own_deal(db: Session, user: User, deal_id: int) -> Deal | None:
    deal = db.get(Deal, deal_id)
    if deal is None or deal.company_id != user.company_id:
        return None
    return deal


@router.get('/orders/{deal_id}')
def order_card(deal_id: int, request: Request, error: str = '', db: Session = Depends(get_db),
               user: User = Depends(require_role(ROLE_CLIENT))):
    deal = _own_deal(db, user, deal_id)
    if deal is None:
        return RedirectResponse('/cabinet/orders', status_code=303)
    ctx = context(request, db, user, 'orders')
    ctx.update({
        'deal': deal, 'error': error, 'crumb': f'Заказ №{deal.number}',
        'stage': stage_info(deal), 'stage_key': stage_key(deal),
        'can_upload_receipt': client_can_upload_receipt(deal),
        'files': [d for d in deal.files if d.visible_to_client],
    })
    return templates.TemplateResponse(request, 'client/order.html', ctx)


@router.post('/orders/{deal_id}/documents')
def upload_client_document(deal_id: int, doc_type: str = Form('receipt'), title: str = Form(''),
                           file: UploadFile = File(...), db: Session = Depends(get_db),
                           user: User = Depends(require_role(ROLE_CLIENT))):
    """Покупатель прикладывает чек об оплате — заказ уходит на проверку к менеджеру."""
    deal = _own_deal(db, user, deal_id)
    if deal is None:
        return RedirectResponse('/cabinet/orders', status_code=303)
    if doc_type == 'receipt' and not client_can_upload_receipt(deal):
        return RedirectResponse(f'/cabinet/orders/{deal_id}?error=Чек можно приложить только '
                                f'после выставления счёта.', status_code=303)

    try:
        saved = save_upload(file, deal.id)
    except UploadError as exc:
        return RedirectResponse(f'/cabinet/orders/{deal_id}?error={exc}', status_code=303)

    doc = Document(
        deal_id=deal.id,
        title=title.strip() or ('Чек об оплате' if doc_type == 'receipt' else saved['file_name']),
        kind=saved['kind'], status='Загружен клиентом', status_tone='blue',
        size_label=saved['size_label'], date_label=f'{saved["uploaded_at"]:%d.%m.%Y}',
        doc_type='receipt' if doc_type == 'receipt' else 'other',
        file_name=saved['file_name'], stored_name=saved['stored_name'],
        size_bytes=saved['size_bytes'], uploaded_at=saved['uploaded_at'],
        uploaded_by_id=user.id, visible_to_client=True,
    )
    db.add(doc)
    db.commit()

    if doc.doc_type == 'receipt':
        attach_receipt(db, deal, doc)
    return RedirectResponse(f'/cabinet/orders/{deal_id}', status_code=303)


@router.post('/training/confirm')
def confirm_training(request: Request, db: Session = Depends(get_db),
                     user: User = Depends(require_role(ROLE_CLIENT))):
    deal = get_deal(db, user)
    if deal and deal.training and not deal.training.confirmed:
        deal.training.confirmed = True
        deal.training.confirmed_at = datetime.now()
        db.add(LeadRequest(name=user.full_name, phone=user.phone, email=user.email,
                           farm=user.company.name if user.company else '',
                           comment=f'Клиент подтвердил дату обучения: {deal.training.date_label}, '
                                   f'{deal.training.participants} участника.',
                           source='Кабинет клиента · обучение', user_id=user.id))
        db.commit()
    return RedirectResponse('/cabinet/training', status_code=303)


@router.post('/message')
def send_message(request: Request, topic: str = Form('Вопрос по сделке'), text: str = Form(...),
                 db: Session = Depends(get_db), user: User = Depends(require_role(ROLE_CLIENT))):
    db.add(LeadRequest(name=user.full_name, phone=user.phone, email=user.email,
                       farm=user.company.name if user.company else '',
                       comment=text.strip(), source=f'Кабинет клиента · {topic}', user_id=user.id))
    db.commit()
    return RedirectResponse(f'/cabinet/{"specialist" if topic == "Специалист" else "config"}?sent=1',
                            status_code=303)
