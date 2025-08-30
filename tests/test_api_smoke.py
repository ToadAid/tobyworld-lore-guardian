from fastapi.testclient import TestClient
from tobyworld.api.server import app

client = TestClient(app)


def test_ask_smoke():
    r = client.post("/ask", json={"user": "frog", "question": "What is Tobyworld?"})
    assert r.status_code == 200
    j = r.json()
    assert "answer" in j
    assert "meta" in j
    assert isinstance(j["meta"].get("docs_used"), int)


def test_health_and_probes():
    # /health
    r = client.get("/health")
    assert r.status_code == 200
    j = r.json()
    assert j.get("ok") is True
    assert "version" in j

    # /healthz
    assert client.get("/healthz").status_code == 200
    # /readyz
    assert client.get("/readyz").status_code == 200
    # /livez
    assert client.get("/livez").status_code == 200


def test_root_redirects_to_docs():
    r = client.get("/", allow_redirects=False)
    assert r.status_code in (301, 302, 303, 307, 308)
    loc = r.headers.get("location", "")
    assert "/docs" in loc
