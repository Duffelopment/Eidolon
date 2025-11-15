"""Application entrypoint for the Eidolon investigative toolkit."""
from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import crud
from .database import Base, engine, get_db
from .routers import apis, scans

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Eidolon Investigative Toolkit", version="1.0.0")

static_dir = Path(__file__).parent / "static"
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

app.include_router(scans.router)
app.include_router(apis.router)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, db=Depends(get_db)):
    scans = [scan for scan in crud.list_scans(db)]
    apis_config = [api for api in crud.list_api_endpoints(db)]
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "scans": scans,
            "apis": apis_config,
        },
    )
