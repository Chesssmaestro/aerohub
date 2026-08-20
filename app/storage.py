"""Приём и хранение файлов, приложенных к заказу."""

import re
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import UploadFile

from .config import ALLOWED_EXTENSIONS, MAX_UPLOAD_BYTES, MEDIA_DIR

CHUNK = 1024 * 1024


class UploadError(Exception):
    pass


def human_size(size: int) -> str:
    if size >= 1024 * 1024:
        return f'{size / 1024 / 1024:.1f} МБ'.replace('.', ',')
    if size >= 1024:
        return f'{size / 1024:.0f} КБ'
    return f'{size} Б'


def safe_name(name: str) -> str:
    """Убирает путь и опасные символы из имени, оставляя его читаемым."""
    name = Path(name or '').name
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]', '_', name).strip(' .')
    return name[:120] or 'file'


def deal_dir(deal_id: int) -> Path:
    path = MEDIA_DIR / 'deals' / str(deal_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_upload(upload: UploadFile, deal_id: int) -> dict:
    """Сохраняет файл на диск и возвращает данные для карточки документа."""
    original = safe_name(upload.filename)
    ext = Path(original).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise UploadError(f'Формат {ext or "без расширения"} не поддерживается. '
                          f'Разрешены документы, таблицы, изображения и архивы.')

    stored = f'{uuid.uuid4().hex}{ext}'
    target = deal_dir(deal_id) / stored
    size = 0
    try:
        with target.open('wb') as out:
            while chunk := upload.file.read(CHUNK):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise UploadError(f'Файл больше {MAX_UPLOAD_BYTES // 1024 // 1024} МБ.')
                out.write(chunk)
    except UploadError:
        target.unlink(missing_ok=True)
        raise
    if size == 0:
        target.unlink(missing_ok=True)
        raise UploadError('Файл пустой.')

    return {
        'file_name': original,
        'stored_name': stored,
        'size_bytes': size,
        'size_label': human_size(size),
        'kind': ext.lstrip('.').upper() or 'FILE',
        'uploaded_at': datetime.now(),
    }


def file_path(deal_id: int, stored_name: str) -> Path:
    return MEDIA_DIR / 'deals' / str(deal_id) / stored_name


def delete_file(deal_id: int, stored_name: str) -> None:
    if stored_name:
        file_path(deal_id, stored_name).unlink(missing_ok=True)
