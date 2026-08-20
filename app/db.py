from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import DB_URL

# check_same_thread понимает только драйвер SQLite, остальным его передавать нельзя
CONNECT_ARGS = {'check_same_thread': False} if DB_URL.startswith('sqlite') else {}
engine = create_engine(DB_URL, connect_args=CONNECT_ARGS)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


# Зависимость FastAPI: сессия БД на один запрос
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
