from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import (ROLE_STAFF, Deal, DealerOrder, Document, Lead, Part, Request as LeadRequest,
                      RoiCalculation, StaffRole, User)
from ..orders import (STAFF_ACTIONS, STAFF_REJECTIONS, attach_invoice, move_to, stage_info,
                      stage_key)
from ..security import require_role
from ..seed import DEPT_TITLES, PIPELINE
from ..storage import UploadError, delete_file, save_upload
from ..templating import templates

router = APIRouter(prefix='/staff')

# Кто видит карточки других должностей и входящие заявки
ALL_ROLES_VIEWERS = {'ceo', 'coo'}
REQUEST_VIEWERS = {'ceo', 'coo', 'sales_head', 'sales_manager', 'service_head', 'service_coordinator'}
# Кто ведёт заказы клиентов и прикладывает к ним документы
ORDER_VIEWERS = REQUEST_VIEWERS | {'accountant', 'warehouse', 'auc_head', 'engineer'}
# Кто ведёт склад запчастей: цены и наличие
WAREHOUSE_KEEPERS = {'ceo', 'coo', 'warehouse', 'accountant', 'service_head', 'engineer',
                     'service_coordinator'}


def departments(db: Session) -> list[tuple[str, list[StaffRole]]]:
    roles = list(db.scalars(select(StaffRole).order_by(StaffRole.position)))
    groups = []
    for dept, title in DEPT_TITLES.items():
        items = [r for r in roles if r.dept == dept]
        if items:
            groups.append((title, items))
    return groups


CRUMBS = {'role': None, 'requests': 'Входящие заявки', 'orders': 'Заказы клиентов',
          'parts': 'Склад запчастей'}


def context(request: Request, db: Session, user: User, role: StaffRole, section: str) -> dict:
    # Заказы, где ход за нами: принять заявку, выставить счёт, проверить чек, отгрузить
    our_move = len([d for d in db.scalars(select(Deal))
                    if stage_info(d)['actor'] == 'staff'])
    return {
        'request': request, 'user': user, 'role': role, 'active': section,
        'crumb': CRUMBS.get(section) or role.name,
        'groups': departments(db), 'pipeline': PIPELINE,
        'can_view_all': user.staff_role in ALL_ROLES_VIEWERS,
        'can_view_requests': user.staff_role in REQUEST_VIEWERS,
        'can_view_orders': user.staff_role in ORDER_VIEWERS,
        'can_keep_warehouse': user.staff_role in WAREHOUSE_KEEPERS,
        'org_name': 'АЭРОХАБ',
        'org_sub': f'{user.full_name} · {role.name}',
        'notifications': db.query(LeadRequest).filter(LeadRequest.status == 'Новая').count()
                         + our_move,
    }


def own_role(db: Session, user: User) -> StaffRole | None:
    if not user.staff_role:
        return None
    return db.scalar(select(StaffRole).where(StaffRole.key == user.staff_role))


@router.get('')
def staff_root(request: Request, db: Session = Depends(get_db),
               user: User = Depends(require_role(ROLE_STAFF))):
    role = own_role(db, user)
    if role is None:
        return templates.TemplateResponse(request, 'staff/no_role.html',
                                          {'user': user, 'groups': departments(db),
                                           'active': 'role', 'crumb': 'Роль не назначена',
                                           'org_name': 'АЭРОХАБ', 'org_sub': user.full_name,
                                           'can_view_all': False, 'can_view_requests': False,
                                           'role': None})
    return templates.TemplateResponse(request, 'staff/role.html',
                                      context(request, db, user, role, 'role'))


@router.get('/requests')
def staff_requests(request: Request, db: Session = Depends(get_db),
                   user: User = Depends(require_role(ROLE_STAFF))):
    role = own_role(db, user)
    if role is None or user.staff_role not in REQUEST_VIEWERS:
        return RedirectResponse('/staff', status_code=303)
    ctx = context(request, db, user, role, 'requests')
    ctx.update({
        'requests': list(db.scalars(select(LeadRequest).order_by(LeadRequest.id.desc()))),
        'dealer_orders': list(db.scalars(select(DealerOrder).order_by(DealerOrder.id.desc()))),
        'leads': list(db.scalars(select(Lead).order_by(Lead.id.desc()))),
        'roi_calcs': list(db.scalars(select(RoiCalculation).order_by(RoiCalculation.id.desc()).limit(10))),
    })
    return templates.TemplateResponse(request, 'staff/requests.html', ctx)


def _order_guard(db: Session, user: User) -> StaffRole | None:
    """Возвращает роль сотрудника, если ему доступны заказы клиентов."""
    role = own_role(db, user)
    if role is None or user.staff_role not in ORDER_VIEWERS:
        return None
    return role


@router.get('/orders')
def staff_orders(request: Request, db: Session = Depends(get_db),
                 user: User = Depends(require_role(ROLE_STAFF))):
    role = _order_guard(db, user)
    if role is None:
        return RedirectResponse('/staff', status_code=303)
    ctx = context(request, db, user, role, 'orders')
    deals = list(db.scalars(select(Deal).order_by(Deal.id.desc())))
    ctx['deals'] = deals
    ctx['stage_of'] = {d.id: stage_info(d) for d in deals}
    return templates.TemplateResponse(request, 'staff/orders.html', ctx)


@router.get('/orders/{deal_id}')
def staff_order(deal_id: int, request: Request, error: str = '', db: Session = Depends(get_db),
                user: User = Depends(require_role(ROLE_STAFF))):
    role = _order_guard(db, user)
    if role is None:
        return RedirectResponse('/staff', status_code=303)
    deal = db.get(Deal, deal_id)
    if deal is None:
        return RedirectResponse('/staff/orders', status_code=303)
    ctx = context(request, db, user, role, 'orders')
    ctx.update({
        'deal': deal, 'error': error, 'crumb': f'Заказ №{deal.number}',
        'stage': stage_info(deal), 'stage_key': stage_key(deal),
        'action': STAFF_ACTIONS.get(stage_key(deal)),
        'rejection': STAFF_REJECTIONS.get(stage_key(deal)),
        'needs_invoice': stage_key(deal) in ('new', 'agreed'),
    })
    return templates.TemplateResponse(request, 'staff/order.html', ctx)


@router.post('/orders/{deal_id}/documents')
def upload_document(deal_id: int, title: str = Form(''), visible: str = Form(''),
                    doc_type: str = Form('other'), file: UploadFile = File(...),
                    db: Session = Depends(get_db),
                    user: User = Depends(require_role(ROLE_STAFF))):
    """Сотрудник прикладывает файл к заказу. Счёт-фактура двигает заказ на этап оплаты."""
    if _order_guard(db, user) is None:
        return RedirectResponse('/staff', status_code=303)
    deal = db.get(Deal, deal_id)
    if deal is None:
        return RedirectResponse('/staff/orders', status_code=303)

    try:
        saved = save_upload(file, deal.id)
    except UploadError as exc:
        return RedirectResponse(f'/staff/orders/{deal_id}?error={exc}', status_code=303)

    is_invoice = doc_type == 'invoice'
    doc = Document(
        deal_id=deal.id,
        title=title.strip() or ('Счёт-фактура' if is_invoice else saved['file_name']),
        kind=saved['kind'],
        status='Счёт выставлен' if is_invoice else 'Загружен',
        status_tone='warn' if is_invoice else 'ok',
        size_label=saved['size_label'],
        date_label=f'{saved["uploaded_at"]:%d.%m.%Y}',
        doc_type='invoice' if is_invoice else 'other',
        file_name=saved['file_name'],
        stored_name=saved['stored_name'],
        size_bytes=saved['size_bytes'],
        uploaded_at=saved['uploaded_at'],
        uploaded_by_id=user.id,
        # счёт клиент должен видеть всегда
        visible_to_client=True if is_invoice else bool(visible),
    )
    db.add(doc)
    db.commit()

    if is_invoice:
        attach_invoice(db, deal, doc)
    return RedirectResponse(f'/staff/orders/{deal_id}', status_code=303)


@router.post('/orders/{deal_id}/documents/{doc_id}/visibility')
def toggle_visibility(deal_id: int, doc_id: int, db: Session = Depends(get_db),
                      user: User = Depends(require_role(ROLE_STAFF))):
    if _order_guard(db, user) is None:
        return RedirectResponse('/staff', status_code=303)
    doc = db.get(Document, doc_id)
    if doc and doc.deal_id == deal_id:
        doc.visible_to_client = not doc.visible_to_client
        db.commit()
    return RedirectResponse(f'/staff/orders/{deal_id}', status_code=303)


@router.post('/orders/{deal_id}/documents/{doc_id}/delete')
def remove_document(deal_id: int, doc_id: int, db: Session = Depends(get_db),
                    user: User = Depends(require_role(ROLE_STAFF))):
    if _order_guard(db, user) is None:
        return RedirectResponse('/staff', status_code=303)
    doc = db.get(Document, doc_id)
    if doc and doc.deal_id == deal_id:
        delete_file(deal_id, doc.stored_name)
        db.delete(doc)
        db.commit()
    return RedirectResponse(f'/staff/orders/{deal_id}', status_code=303)


@router.post('/orders/{deal_id}/stage')
def change_stage(deal_id: int, decision: str = Form('next'), comment: str = Form(''),
                 db: Session = Depends(get_db),
                 user: User = Depends(require_role(ROLE_STAFF))):
    """Единственный способ двигать заказ: кнопка действия, доступная на текущем этапе."""
    if _order_guard(db, user) is None:
        return RedirectResponse('/staff', status_code=303)
    deal = db.get(Deal, deal_id)
    if deal is None:
        return RedirectResponse('/staff/orders', status_code=303)

    table = STAFF_REJECTIONS if decision == 'reject' else STAFF_ACTIONS
    step = table.get(stage_key(deal))
    if step is None:
        return RedirectResponse(f'/staff/orders/{deal_id}', status_code=303)

    _, target, log_title = step
    note = f'{user.full_name}, {role_name(db, user)}'
    if comment.strip():
        note += f' · {comment.strip()}'
    move_to(db, deal, target, log_title, note)
    return RedirectResponse(f'/staff/orders/{deal_id}', status_code=303)


def role_name(db: Session, user: User) -> str:
    role = own_role(db, user)
    return role.name if role else 'сотрудник'


@router.get('/parts')
def staff_parts(request: Request, q: str = '', group: str = '', page: int = 1,
                saved: str = '', db: Session = Depends(get_db),
                user: User = Depends(require_role(ROLE_STAFF))):
    """Склад запчастей: поиск по каталогу, правка цены и наличия."""
    role = own_role(db, user)
    if role is None or user.staff_role not in WAREHOUSE_KEEPERS:
        return RedirectResponse('/staff', status_code=303)

    query = select(Part)
    if q.strip():
        needle = f'%{q.strip()}%'
        query = query.where(or_(Part.name.ilike(needle), Part.article.ilike(needle)))
    if group:
        query = query.where(Part.group == group)

    per_page = 30
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    pages = max(1, -(-total // per_page))
    page = max(1, min(page, pages))
    items = list(db.scalars(query.order_by(Part.name).offset((page - 1) * per_page).limit(per_page)))

    ctx = context(request, db, user, role, 'parts')
    # ключи не должны пересекаться с items/groups сайдбара ролей
    ctx.update({
        'parts': items, 'total': total, 'page': page, 'pages': pages, 'q': q, 'group': group,
        'saved': bool(saved),
        'part_groups': [(value, count) for value, count in
                        db.execute(select(Part.group, func.count()).group_by(Part.group)
                                   .order_by(func.count().desc())) if value],
        'catalog_size': db.scalar(select(func.count()).select_from(Part)) or 0,
        'in_stock': db.scalar(select(func.count()).select_from(Part)
                              .where(Part.stock.notin_(['Под заказ', 'Нет', 'Снят с продажи']))) or 0,
        'stock_value': db.scalar(select(func.sum(Part.price)).select_from(Part)) or 0,
    })
    return templates.TemplateResponse(request, 'staff/parts.html', ctx)


@router.post('/parts/{part_id}')
def update_part(part_id: int, price: float = Form(...), stock: str = Form(...),
                q: str = Form(''), group: str = Form(''), page: int = Form(1),
                db: Session = Depends(get_db),
                user: User = Depends(require_role(ROLE_STAFF))):
    if user.staff_role not in WAREHOUSE_KEEPERS:
        return RedirectResponse('/staff', status_code=303)
    part = db.get(Part, part_id)
    if part:
        part.price = max(0, price)
        part.stock = stock.strip() or 'Под заказ'
        db.commit()
    url = f'/staff/parts?q={q}&group={group}&page={page}&saved=1'
    return RedirectResponse(url, status_code=303)


@router.get('/role/{key}')
def staff_role(key: str, request: Request, db: Session = Depends(get_db),
               user: User = Depends(require_role(ROLE_STAFF))):
    if user.staff_role not in ALL_ROLES_VIEWERS and key != user.staff_role:
        return RedirectResponse('/staff', status_code=303)
    role = db.scalar(select(StaffRole).where(StaffRole.key == key))
    if role is None:
        return RedirectResponse('/staff', status_code=303)
    return templates.TemplateResponse(request, 'staff/role.html',
                                      context(request, db, user, role, 'role'))
