from fastapi.testclient import TestClient
from tobyworld.api.server import app

# Do not follow redirects globally
client = TestClient(app, follow_redirects=False)

def test_ask_smoke():
    r = client.post("/ask", json={"user": "frog", "question": "What is Tobyworld?"})
    assert r.status_code == 200
    j = r.json()
    assert "answer" in j
    assert "meta" in j
    assert isinstance(j["meta"].get("docs_used"), int)

def test_health_and_probes():
    r = client.get("/health")
    assert r.status_code == 200
    j = r.json()
    assert j.get("ok") is True
    assert "version" in j

    assert client.get("/healthz").status_code == 200
    assert client.get("/readyz").status_code == 200
    assert client.get("/livez").status_code == 200

def test_root_redirects_to_docs():
    r = client.get("/")  # no extra kwargs needed
    assert r.status_code in (301, 302, 303, 307, 308)
    assert "/docs" in r.headers.get("location", "")
