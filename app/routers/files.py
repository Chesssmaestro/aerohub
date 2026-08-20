from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import ROLE_CLIENT, ROLE_STAFF, Document, User
from ..security import LoginRequired, get_current_user
from ..storage import file_path

router = APIRouter()


def can_read(doc: Document, user: User | None) -> bool:
    if user is None:
        return False
    if user.role == ROLE_STAFF:
        return True
    if user.role == ROLE_CLIENT:
        return doc.visible_to_client and doc.deal.company_id == user.company_id
    return False


@router.get('/files/{doc_id}')
def download(doc_id: int, db: Session = Depends(get_db),
             user: User | None = Depends(get_current_user)):
    doc = db.get(Document, doc_id)
    if doc is None or not doc.stored_name:
        raise HTTPException(status_code=404, detail='Файл не найден')
    if user is None:
        raise LoginRequired(f'/files/{doc_id}')
    if not can_read(doc, user):
        raise HTTPException(status_code=403, detail='Нет доступа к файлу')

    path = file_path(doc.deal_id, doc.stored_name)
    if not path.exists():
        raise HTTPException(status_code=404, detail='Файл не найден на диске')
    return FileResponse(path, filename=doc.file_name or doc.stored_name)
