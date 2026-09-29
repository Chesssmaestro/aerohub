"""Профиль пользователя: личные данные и смена пароля — общий для всех кабинетов.

Страница профиля рисуется в своём кабинете (/cabinet/profile, /dealer/profile, /staff/profile),
а сохранение идёт сюда и возвращает обратно с кодом результата в ?msg=.
"""

from fastapi import APIRouter, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User
from ..security import get_current_user, hash_password, verify_password

router = APIRouter(prefix='/profile')


def back(user: User, msg: str) -> RedirectResponse:
    return RedirectResponse(f'{user.profile_url}?msg={msg}', status_code=303)


@router.post('')
def update_profile(full_name: str = Form(''), phone: str = Form(''),
                   db: Session = Depends(get_db), user: User | None = Depends(get_current_user)):
    if user is None:
        return RedirectResponse('/login', status_code=303)
    full_name = full_name.strip()
    if len(full_name) < 2:
        return back(user, 'name')
    user.full_name = full_name[:120]
    user.phone = phone.strip()[:40]
    db.commit()
    return back(user, 'saved')


@router.post('/password')
def change_password(current: str = Form(''), new: str = Form(''), repeat: str = Form(''),
                    db: Session = Depends(get_db), user: User | None = Depends(get_current_user)):
    if user is None:
        return RedirectResponse('/login', status_code=303)
    if not verify_password(current, user.password_hash):
        return back(user, 'pw_wrong')
    if len(new) < 8:
        return back(user, 'pw_short')
    if new != repeat:
        return back(user, 'pw_mismatch')
    user.password_hash = hash_password(new)
    db.commit()
    return back(user, 'pw_ok')
