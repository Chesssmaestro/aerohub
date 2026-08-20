import hashlib
import hmac
import os

from fastapi import Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from .db import get_db
from .models import User

ITERATIONS = 240_000


class LoginRequired(Exception):
    """Пользователь не авторизован — редиректим на форму входа."""

    def __init__(self, next_url: str = '/'):
        self.next_url = next_url


class WrongRole(Exception):
    """Кабинет чужой роли — уводим в свой."""

    def __init__(self, home_url: str = '/'):
        self.home_url = home_url


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, ITERATIONS)
    return f'pbkdf2_sha256${ITERATIONS}${salt.hex()}${digest.hex()}'


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations, salt_hex, digest_hex = stored.split('$')
    except ValueError:
        return False
    if algo != 'pbkdf2_sha256':
        return False
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt_hex), int(iterations))
    return hmac.compare_digest(digest.hex(), digest_hex)


def login_user(request: Request, user: User) -> None:
    request.session['user_id'] = user.id


def logout_user(request: Request) -> None:
    request.session.clear()


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    """Текущий пользователь или None — для публичных страниц."""
    user_id = request.session.get('user_id')
    if not user_id:
        return None
    return db.get(User, user_id)


def require_role(role: str):
    """Зависимость: пускает в кабинет только свою роль."""

    def dependency(request: Request, user: User | None = Depends(get_current_user)) -> User:
        if user is None:
            raise LoginRequired(request.url.path)
        if user.role != role:
            raise WrongRole(user.home_url)
        return user

    return dependency


def redirect_to_login(next_url: str = '/') -> RedirectResponse:
    return RedirectResponse(f'/login?next={next_url}', status_code=303)
