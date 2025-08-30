from fastapi import FastAPI
from ..core.mirror import MirrorCore
from ..core.config import Config
from fastapi.responses import RedirectResponse, JSONResponse

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


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")

@app.get("/healthz", include_in_schema=False)
def healthz():
    # alias for Kubernetes-style probes
    return {"ok": True, "version": core.cfg.version}

@app.get("/readyz", include_in_schema=False)
def readyz():
    # extend later: check FAISS index, model, etc.
    return {"ready": True}

@app.get("/livez", include_in_schema=False)
def livez():
    return {"live": True}
