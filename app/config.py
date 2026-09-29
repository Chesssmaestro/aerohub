import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def env(name: str) -> str:
    """AEROHUB_<name>. Пустая переменная считается незаданной — иначе вход и регистрация ломаются молча."""
    return os.getenv(f'AEROHUB_{name}') or ''


# Ключ подписи cookie-сессии. В проде задаётся переменной окружения.
SECRET_KEY = env('SECRET_KEY') or 'aerohub-dev-secret-change-me'
# Код приглашения для регистрации сотрудника.
STAFF_CODE = env('STAFF_CODE') or 'AEROHUB2026'

DB_URL = env('DB_URL') or f'sqlite:///{BASE_DIR / "aerohub.db"}'

# Хранилище файлов, приложенных к заказам
MEDIA_DIR = BASE_DIR / 'media'
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
ALLOWED_EXTENSIONS = {
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.csv', '.txt', '.rtf', '.odt', '.ods',
    '.jpg', '.jpeg', '.png', '.webp', '.heic', '.zip', '.rar', '.7z', '.dwg', '.kml', '.kmz',
}

# Администратор портала — создаётся при первом запуске на пустой базе.
# Пароль в проде задаётся переменной окружения и меняется в профиле.
ADMIN_EMAIL = env('ADMIN_EMAIL') or 'admin@aerohub.ru'
ADMIN_PASSWORD = env('ADMIN_PASSWORD') or 'aerohub-admin'

COMPANY = {
    'name': 'АЭРОХАБ',
    'city': 'Самара',
    'phone': '+7 846 000-00-00',
    'email': 'info@aerohub.example',
}
