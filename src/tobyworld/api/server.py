from fastapi import FastAPI
from ..core.mirror import MirrorCore
from ..core.config import Config

app = FastAPI(title="Tobyworld Mirror V3")
core = MirrorCore(Config())

@app.get("/health")
def health():
    return {"ok": True, "version": core.cfg.version}

@app.get("/diag")
def diag():
    return {"recent": core.ledger.recent(5)}

@app.post("/ask")
def ask(payload: dict):
    user = payload.get("user","anon")
    q = (payload.get("question") or "").strip()
    return core.ask(user, q)
