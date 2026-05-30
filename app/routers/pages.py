"""Server-rendered page routes (Jinja2 templates)."""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import settings

router = APIRouter(tags=["pages"], include_in_schema=False)
templates = Jinja2Templates(directory="app/templates")


def _ctx(request: Request, **kwargs):
    base = {"request": request, "app_name": settings.app_name, "year": 2026}
    base.update(kwargs)
    return base


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", _ctx(request))


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", _ctx(request, mode="login"))


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("login.html", _ctx(request, mode="register"))


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", _ctx(request))


@router.get("/report/{analysis_id}", response_class=HTMLResponse)
async def report_page(request: Request, analysis_id: str):
    return templates.TemplateResponse(
        "report.html", _ctx(request, analysis_id=analysis_id)
    )
