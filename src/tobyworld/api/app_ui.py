# src/tobyworld/api/app_ui.py
from __future__ import annotations
from typing import Callable, Dict, Any
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
import importlib.resources as pkgres

def build_app_router() -> APIRouter:
    r = APIRouter()

    @r.get("/app", include_in_schema=False)
    def app_page():
        html = pkgres.files("tobyworld.web").joinpath("app.html").read_text(encoding="utf-8")
        return HTMLResponse(html)

    return r
