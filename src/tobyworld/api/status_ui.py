# src/tobyworld/api/status_ui.py
from __future__ import annotations
from typing import Callable, Dict, Any
from fastapi import APIRouter
from fastapi.responses import JSONResponse, HTMLResponse
import importlib.resources as pkgres

def build_status_router(get_status: Callable[[], Dict[str, Any]]) -> APIRouter:
    """
    You pass in a function that returns a status dict.
    This module serves /debug/status (JSON) and /status (HTML) using that data.
    """
    r = APIRouter()

    @r.get("/debug/status")
    def debug_status():
        try:
            return JSONResponse(get_status())
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    @r.get("/status", include_in_schema=False)
    def status_page():
        # load the packaged HTML (tobyworld.web.status)
        html = pkgres.files("tobyworld.web").joinpath("status.html").read_text(encoding="utf-8")
        return HTMLResponse(html)

    return r
