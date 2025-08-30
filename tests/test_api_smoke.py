from fastapi.testclient import TestClient
from tobyworld.api.server import app

# Do not follow redirects globally
client = TestClient(app, follow_redirects=False)


def test_ask_smoke():
    r = client.post("/ask", json={"user": "frog", "question": "What is Tobyworld?"})
    assert r.status_code == 200
    j = r.json()
    assert "answer" in j
    assert "meta" in j and isinstance(j["meta"], dict)
    # if present, docs_used should be an int
    if "docs_used" in j["meta"]:
        assert isinstance(j["meta"]["docs_used"], int)


def test_health_and_diag():
    # /health
    r = client.get("/health")
    assert r.status_code == 200
    j = r.json()
    assert j.get("ok") is True
    assert isinstance(j.get("version"), str)

    # /diag (with query)
    r = client.get("/diag", params={"n": 3})
    assert r.status_code == 200
    d = r.json()
    assert "uptime_seconds" in d and isinstance(d["uptime_seconds"], (int, float))
    assert "requests" in d and isinstance(d["requests"], dict)
    assert "recent" in d and isinstance(d["recent"], list)


def test_root_redirects_to_docs():
    r = client.get("/")  # no extra kwargs needed
    assert r.status_code in (301, 302, 303, 307, 308)
    assert "/docs" in r.headers.get("location", "")


def test_metrics_exposes_counters():
    # exercise routes to bump counters
    client.get("/health")
    client.get("/diag")
    client.post("/ask", json={"user": "test", "question": "ping?"})

    r = client.get("/metrics")
    assert r.status_code == 200
    body = r.text

    # basic presence checks
    assert 'tw_requests_total{route="health"}' in body
    assert 'tw_requests_total{route="diag"}' in body
    assert 'tw_requests_total{route="ask"}' in body
    assert "tw_uptime_seconds" in body
    # latency histogram should have a count line for at least one route
    assert 'tw_request_latency_seconds_count{route="ask"}' in body
