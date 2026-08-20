from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import STAFF_CODE
from ..db import get_db
from ..models import ROLE_CLIENT, ROLE_DEALER, ROLE_HOME, ROLE_STAFF, Company, StaffRole, User
from ..security import get_current_user, hash_password, login_user, logout_user, verify_password
from ..templating import templates

router = APIRouter()

PORTALS = [
    {
        'key': ROLE_CLIENT,
        'title': 'Кабинет покупателя',
        'text': 'Сделка, поставка, документы, обучение, эксплуатация и сервис по вашей технике.',
        'icon': '<path d="M4 20v-2a4 4 0 014-4h8a4 4 0 014 4v2" stroke="currentColor" stroke-width="1.6"/>'
                '<circle cx="12" cy="7" r="3.4" stroke="currentColor" stroke-width="1.6"/>',
    },
    {
        'key': ROLE_DEALER,
        'title': 'Кабинет поставщика',
        'text': 'Оптовые заявки, цены и маржа, ваши клиенты, обучение и маркетинговые материалы.',
        'icon': '<path d="M3 21h18M5 21V9l7-5 7 5v12M9 21v-6h6v6" stroke="currentColor" stroke-width="1.6"/>',
    },
    {
        'key': ROLE_STAFF,
        'title': 'Кабинет сотрудника',
        'text': 'Процессы, KPI, правила и задачи запуска — по вашей роли в компании.',
        'icon': '<rect x="3" y="4" width="18" height="16" rx="1" stroke="currentColor" stroke-width="1.6"/>'
                '<path d="M3 9h18M8 4v5" stroke="currentColor" stroke-width="1.6"/>',
    },
]

PORTAL_TITLES = {p['key']: p['title'] for p in PORTALS}


def _staff_roles(db: Session) -> list[StaffRole]:
    return list(db.scalars(select(StaffRole).order_by(StaffRole.position)))


@router.get('/login')
def login_page(request: Request, portal: str | None = None, next: str = '',
               db: Session = Depends(get_db), user: User | None = Depends(get_current_user)):
    if user:
        return RedirectResponse(user.home_url, status_code=303)
    if portal not in PORTAL_TITLES:
        portal = None
    return templates.TemplateResponse(request, 'auth/login.html', {
        'user': None, 'portals': PORTALS, 'portal': portal,
        'portal_title': PORTAL_TITLES.get(portal, ''), 'next': next,
        'staff_roles': _staff_roles(db) if portal == ROLE_STAFF else [],
    })


@router.post('/login')
def login_submit(request: Request, email: str = Form(...), password: str = Form(...),
                 portal: str = Form(''), next: str = Form(''), db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(request, 'auth/login.html', {
            'user': None, 'portals': PORTALS, 'portal': portal or None,
            'portal_title': PORTAL_TITLES.get(portal, ''), 'next': next,
            'staff_roles': _staff_roles(db) if portal == ROLE_STAFF else [],
            'error': 'Неверная почта или пароль.', 'email': email,
        }, status_code=400)

    if portal and user.role != portal:
        return templates.TemplateResponse(request, 'auth/login.html', {
            'user': None, 'portals': PORTALS, 'portal': portal,
            'portal_title': PORTAL_TITLES.get(portal, ''), 'next': next,
            'staff_roles': _staff_roles(db) if portal == ROLE_STAFF else [],
            'error': f'Этот аккаунт зарегистрирован как «{user.role_title}». '
                     f'Выберите нужный кабинет на предыдущем шаге.',
            'email': email,
        }, status_code=400)

    login_user(request, user)
    target = next if next.startswith('/') else ROLE_HOME.get(user.role, '/')
    return RedirectResponse(target, status_code=303)


@router.get('/register')
def register_page(request: Request, portal: str | None = None,
                  db: Session = Depends(get_db), user: User | None = Depends(get_current_user)):
    if user:
        return RedirectResponse(user.home_url, status_code=303)
    if portal not in PORTAL_TITLES:
        portal = None
    return templates.TemplateResponse(request, 'auth/register.html', {
        'user': None, 'portals': PORTALS, 'portal': portal,
        'portal_title': PORTAL_TITLES.get(portal, ''),
        'staff_roles': _staff_roles(db) if portal == ROLE_STAFF else [],
    })


@router.post('/register')
def register_submit(
    request: Request,
    portal: str = Form(...),
    full_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(''),
    password: str = Form(...),
    password2: str = Form(''),
    company_name: str = Form(''),
    inn: str = Form(''),
    city: str = Form(''),
    staff_role: str = Form(''),
    staff_code: str = Form(''),
    db: Session = Depends(get_db),
):
    email = email.strip().lower()
    ctx = {
        'user': None, 'portals': PORTALS, 'portal': portal,
        'portal_title': PORTAL_TITLES.get(portal, ''),
        'staff_roles': _staff_roles(db) if portal == ROLE_STAFF else [],
        'form': {'full_name': full_name, 'email': email, 'phone': phone,
                 'company_name': company_name, 'inn': inn, 'city': city, 'staff_role': staff_role},
    }

    def fail(message: str):
        return templates.TemplateResponse(request, 'auth/register.html',
                                          {**ctx, 'error': message}, status_code=400)

    if portal not in PORTAL_TITLES:
        return fail('Выберите кабинет.')
    if len(password) < 8:
        return fail('Пароль должен быть не короче 8 символов.')
    if password != password2:
        return fail('Пароли не совпадают.')
    if db.scalar(select(User).where(User.email == email)):
        return fail('Пользователь с такой почтой уже зарегистрирован.')

    company_id = None
    role_key = None

    if portal == ROLE_STAFF:
        if staff_code.strip() != STAFF_CODE:
            return fail('Неверный код приглашения. Получите его у исполнительного директора.')
        role = db.scalar(select(StaffRole).where(StaffRole.key == staff_role))
        if role is None:
            return fail('Выберите должность.')
        role_key = role.key
    else:
        if not company_name.strip():
            return fail('Укажите название организации.')
        company = Company(name=company_name.strip(), inn=inn.strip(), city=city.strip(),
                          kind=portal, dealer_level='Silver' if portal == ROLE_DEALER else '')
        db.add(company)
        db.flush()
        company_id = company.id

    user = User(email=email, password_hash=hash_password(password), full_name=full_name.strip(),
                phone=phone.strip(), role=portal, staff_role=role_key, company_id=company_id)
    db.add(user)
    db.commit()

    login_user(request, user)
    return RedirectResponse(ROLE_HOME[portal], status_code=303)


@router.post('/logout')
def logout(request: Request):
    logout_user(request)
    return RedirectResponse('/', status_code=303)
