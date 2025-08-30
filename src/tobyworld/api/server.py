# src/tobyworld/api/server.py

import time
from typing import Any, Dict

from fastapi import FastAPI, Query
from fastapi.responses import RedirectResponse, Response
from pydantic import BaseModel

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

from ..core.mirror import MirrorCore
from ..core.config import Config

app = FastAPI(title="Tobyworld Mirror V3")
core = MirrorCore(Config())

# ---------- process state ----------
START_TS = time.time()
REQS_TOTAL: Dict[str, int] = {"health": 0, "diag": 0, "ask": 0}

# Prometheus metrics (scoped to a registry to avoid collisions)
REGISTRY = CollectorRegistry()
REQUEST_COUNT = Counter(
    "tw_requests_total", "Total HTTP requests by route", ["route"], registry=REGISTRY
)
REQUEST_LATENCY = Histogram(
    "tw_request_latency_seconds",
    "HTTP request latency (s) by route",
    ["route"],
    registry=REGISTRY,
)
UPTIME_GAUGE = Gauge("tw_uptime_seconds", "Process uptime in seconds", registry=REGISTRY)

# ---------- Models ----------
class Health(BaseModel):
    ok: bool
    version: str

class Diag(BaseModel):
    uptime_seconds: float
    requests: Dict[str, int]
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
    t0 = time.perf_counter()
    try:
        return Health(ok=True, version=str(core.cfg.version))
    finally:
        REQS_TOTAL["health"] = REQS_TOTAL.get("health", 0) + 1
        REQUEST_COUNT.labels("health").inc()
        REQUEST_LATENCY.labels("health").observe(time.perf_counter() - t0)

@app.get("/diag", response_model=Diag, summary="Diag")
def diag(n: int = Query(5, ge=1, le=50)) -> Diag:
    t0 = time.perf_counter()
    try:
        return Diag(
            uptime_seconds=round(time.time() - START_TS, 3),
            requests=REQS_TOTAL,
            recent=core.ledger.recent(n),
        )
    finally:
        REQS_TOTAL["diag"] = REQS_TOTAL.get("diag", 0) + 1
        REQUEST_COUNT.labels("diag").inc()
        REQUEST_LATENCY.labels("diag").observe(time.perf_counter() - t0)

@app.post("/ask", response_model=AskResponse, summary="Ask")
def ask(req: AskRequest) -> AskResponse:
    t0 = time.perf_counter()
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
    finally:
        REQS_TOTAL["ask"] = REQS_TOTAL.get("ask", 0) + 1
        REQUEST_COUNT.labels("ask").inc()
        REQUEST_LATENCY.labels("ask").observe(time.perf_counter() - t0)

@app.get("/metrics", include_in_schema=False)
def metrics():
    # refresh uptime just-in-time
    UPTIME_GAUGE.set(time.time() - START_TS)
    return Response(generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)

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
