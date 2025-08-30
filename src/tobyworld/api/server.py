# src/tobyworld/api/server.py

from typing import Any, Dict

from fastapi import FastAPI, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from ..core.mirror import MirrorCore
from ..core.config import Config

app = FastAPI(title="Tobyworld Mirror V3")
core = MirrorCore(Config())

# ---------- Models ----------
class Health(BaseModel):
    ok: bool
    version: str

class Diag(BaseModel):
    recent: list[Any]

class AskRequest(BaseModel):
    user: str = "anon"
    question: str

class AskResponse(BaseModel):
    answer: str
    meta: Dict[str, Any] = {}

# ---------- Routes ----------
@app.get("/health", response_model=Health, summary="Health")
def health() -> Health:
    return Health(ok=True, version=str(core.cfg.version))

@app.get("/diag", response_model=Diag, summary="Diag")
def diag(n: int = Query(5, ge=1, le=50)) -> Diag:
    return Diag(recent=core.ledger.recent(n))

@app.post("/ask", response_model=AskResponse, summary="Ask")
def ask(req: AskRequest) -> AskResponse:
    try:
        out = core.ask(req.user, (req.question or "").strip())

        # Normalize common shapes into strict JSON
        if isinstance(out, tuple) and len(out) == 2:
            answer, meta = out
            return AskResponse(
                answer=str(answer),
                meta=meta if isinstance(meta, dict) else {"info": meta},
            )
        if isinstance(out, dict):
            ans = out.get("answer")
            meta = out.get("meta", {})
            return AskResponse(
                answer=str(ans) if ans is not None else str(out),
                meta=meta if isinstance(meta, dict) else {"meta": meta},
            )
        # Fallback: treat as plain answer
        return AskResponse(answer=str(out), meta={})
    except Exception as e:
        # Always return valid JSON even on failure
        return AskResponse(answer="", meta={"error": str(e)})

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")

# Probes
@app.get("/healthz", include_in_schema=False)
def healthz():
    return {"ok": True, "version": core.cfg.version}

@app.get("/readyz", include_in_schema=False)
def readyz():
    return {"ready": True}

@app.get("/livez", include_in_schema=False)
def livez():
    return {"live": True}
