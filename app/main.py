from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from .config import BASE_DIR, SECRET_KEY
from .routers import auth, client, dealer, files, parts, public, staff
from .security import LoginRequired, WrongRole
from .seed import init_db
from .templating import templates

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title='АЭРОХАБ', docs_url=None, redoc_url=None, lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, session_cookie='aerohub_session')
app.mount('/static', StaticFiles(directory=str(BASE_DIR / 'app' / 'static')), name='static')

app.include_router(public.router)
app.include_router(parts.router)
app.include_router(auth.router)
app.include_router(client.router)
app.include_router(dealer.router)
app.include_router(staff.router)
app.include_router(files.router)


@app.exception_handler(LoginRequired)
def handle_login_required(request: Request, exc: LoginRequired):
    return RedirectResponse(f'/login?next={exc.next_url}', status_code=303)


@app.exception_handler(WrongRole)
def handle_wrong_role(request: Request, exc: WrongRole):
    return RedirectResponse(exc.home_url, status_code=303)


@app.exception_handler(404)
def handle_404(request: Request, exc):
    return templates.TemplateResponse(request, 'errors/404.html', {'user': None}, status_code=404)
