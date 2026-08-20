from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..catalog import CROP_SETS, MODELS, OPTIONS, PACKAGES
from ..db import get_db
from ..models import Request as LeadRequest
from ..models import RoiCalculation, User
from ..security import get_current_user
from ..templating import templates

router = APIRouter()


@router.get('/')
def index(request: Request, user: User | None = Depends(get_current_user)):
    return templates.TemplateResponse(request, 'public/index.html', {
        'user': user, 'active': 'home', 'models': MODELS,
    })


@router.get('/roi')
def roi(request: Request, user: User | None = Depends(get_current_user)):
    return templates.TemplateResponse(request, 'public/roi.html', {
        'user': user, 'active': 'roi', 'crop_sets': CROP_SETS, 'models': MODELS,
    })


@router.post('/roi/save')
def roi_save(request: Request, mode: str = Form('own'), area: float = Form(0),
             crops: str = Form(''), passes: int = Form(0), price_per_ha: float = Form(0),
             season_days: int = Form(0), cost_per_ha: float = Form(0),
             season_saving: float = Form(0), payback_months: float = Form(0),
             db: Session = Depends(get_db), user: User | None = Depends(get_current_user)):
    db.add(RoiCalculation(user_id=user.id if user else None, mode=mode, area=area, crops=crops,
                          passes=passes, price_per_ha=price_per_ha, season_days=season_days,
                          cost_per_ha=cost_per_ha, season_saving=season_saving,
                          payback_months=payback_months))
    db.commit()
    return {'saved': True}


@router.get('/configurator')
def configurator(request: Request, user: User | None = Depends(get_current_user)):
    return templates.TemplateResponse(request, 'public/configurator.html', {
        'user': user, 'active': 'configurator', 'models': MODELS,
        'packages': PACKAGES, 'options': OPTIONS,
    })


@router.get('/kp')
def kp_form(request: Request, preset: str = '', user: User | None = Depends(get_current_user)):
    return templates.TemplateResponse(request, 'public/kp.html', {
        'user': user, 'active': 'kp', 'preset': preset,
    })


@router.post('/kp')
def kp_submit(request: Request, name: str = Form(...), phone: str = Form(''),
              email: str = Form(''), farm: str = Form(''), area: str = Form(''),
              comment: str = Form(''), db: Session = Depends(get_db),
              user: User | None = Depends(get_current_user)):
    # Заявку оставляют из-под аккаунта — так она сразу привязана к кабинету
    if user is None:
        return RedirectResponse('/login?next=/kp', status_code=303)
    if not phone.strip() and not email.strip():
        return templates.TemplateResponse(request, 'public/kp.html', {
            'user': user, 'active': 'kp', 'error': 'Укажите телефон или почту для связи.',
            'form': {'name': name, 'phone': phone, 'email': email, 'farm': farm,
                     'area': area, 'comment': comment},
        }, status_code=400)

    db.add(LeadRequest(name=name.strip(), phone=phone.strip(), email=email.strip(),
                       farm=farm.strip(), area=area.strip(), comment=comment.strip(),
                       source='Форма КП', user_id=user.id if user else None))
    db.commit()
    return templates.TemplateResponse(request, 'public/kp.html', {
        'user': user, 'active': 'kp', 'sent': True,
    })


@router.get('/contacts')
def contacts(request: Request, user: User | None = Depends(get_current_user)):
    return templates.TemplateResponse(request, 'public/contacts.html', {
        'user': user, 'active': 'contacts',
    })
