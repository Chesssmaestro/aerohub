import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Ключ подписи cookie-сессии. В проде задаётся переменной окружения.
# `or` вместо второго аргумента getenv: пустая переменная на хостинге тоже
# должна откатываться к дефолту, иначе вход и регистрация ломаются молча.
SECRET_KEY = os.getenv('AEROHUB_SECRET_KEY') or 'aerohub-dev-secret-change-me'
# Код приглашения для регистрации сотрудника.
STAFF_CODE = os.getenv('AEROHUB_STAFF_CODE') or 'AEROHUB2026'

DB_URL = os.getenv('AEROHUB_DB_URL', f'sqlite:///{BASE_DIR / "aerohub.db"}')

# Хранилище файлов, приложенных к заказам
MEDIA_DIR = BASE_DIR / 'media'
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
ALLOWED_EXTENSIONS = {
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.csv', '.txt', '.rtf', '.odt', '.ods',
    '.jpg', '.jpeg', '.png', '.webp', '.heic', '.zip', '.rar', '.7z', '.dwg', '.kml', '.kmz',
}

# Пароль демо-пользователей из сида.
DEMO_PASSWORD = 'demo12345'

COMPANY = {
    'name': 'АЭРОХАБ',
    'city': 'Самара',
    'phone': '+7 846 000-00-00',
    'email': 'info@aerohub.example',
}
