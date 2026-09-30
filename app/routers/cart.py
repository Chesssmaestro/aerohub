from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import CartItem, Part, PartRequestItem, ROLE_CLIENT, User
from ..models import Request as LeadRequest
from ..security import require_role
from ..templating import templates

router = APIRouter()


@router.post('/cart/add')
def cart_add(part_id: int = Form(...), qty: int = Form(1), next: str = Form('/parts'),
            db: Session = Depends(get_db), user: User = Depends(require_role(ROLE_CLIENT))):
    part = db.get(Part, part_id)
    if part is None:
        return RedirectResponse(next, status_code=303)

    qty = max(1, min(qty, 999))
    item = db.scalar(select(CartItem).where(CartItem.user_id == user.id, CartItem.part_id == part_id))
    if item is None:
        item = CartItem(user_id=user.id, part_id=part_id, qty=qty)
        db.add(item)
    else:
        item.qty = min(item.qty + qty, 999)
    db.commit()

    sep = '&' if '?' in next else '?'
    return RedirectResponse(f'{next}{sep}added={part_id}', status_code=303)


@router.post('/cart/update/{item_id}')
def cart_update(item_id: int, qty: int = Form(1), db: Session = Depends(get_db),
                user: User = Depends(require_role(ROLE_CLIENT))):
    item = db.get(CartItem, item_id)
    if item is not None and item.user_id == user.id:
        if qty < 1:
            db.delete(item)
        else:
            item.qty = min(qty, 999)
        db.commit()
    return RedirectResponse('/cart', status_code=303)


@router.post('/cart/remove/{item_id}')
def cart_remove(item_id: int, db: Session = Depends(get_db),
                user: User = Depends(require_role(ROLE_CLIENT))):
    item = db.get(CartItem, item_id)
    if item is not None and item.user_id == user.id:
        db.delete(item)
        db.commit()
    return RedirectResponse('/cart', status_code=303)


@router.get('/cart')
def cart_view(request: Request, sent: str = '', db: Session = Depends(get_db),
             user: User = Depends(require_role(ROLE_CLIENT))):
    items = list(db.scalars(select(CartItem).where(CartItem.user_id == user.id).order_by(CartItem.id)))
    total = sum(i.sum for i in items)
    return templates.TemplateResponse(request, 'public/cart.html', {
        'user': user, 'active': 'cart', 'items': items, 'total': total, 'sent': bool(sent),
    })


@router.post('/cart/checkout')
def cart_checkout(comment: str = Form(''), db: Session = Depends(get_db),
                  user: User = Depends(require_role(ROLE_CLIENT))):
    items = list(db.scalars(select(CartItem).where(CartItem.user_id == user.id).order_by(CartItem.id)))
    if not items:
        return RedirectResponse('/cart', status_code=303)

    lines = [f'{i.part.article} — {i.part.name}, {i.qty} шт. на сумму {int(i.sum)} ₽.' for i in items]
    total = sum(i.sum for i in items)
    lead = LeadRequest(
        name=user.full_name, phone=user.phone, email=user.email,
        farm=user.company.name if user.company else '',
        comment=f'Заказ по корзине запчастей ({len(items)} поз., {int(total)} ₽): '
                + ' '.join(lines) + (f' {comment.strip()}' if comment.strip() else ''),
        source='Запрос по запчасти',
        user_id=user.id,
    )
    db.add(lead)
    db.flush()
    for i in items:
        db.add(PartRequestItem(request_id=lead.id, part_id=i.part_id, qty=i.qty))
        db.delete(i)
    db.commit()
    return RedirectResponse('/cart?sent=1', status_code=303)
