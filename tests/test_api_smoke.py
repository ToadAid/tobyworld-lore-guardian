from fastapi.testclient import TestClient
from tobyworld.api.server import app

# Do not follow redirects globally
client = TestClient(app, follow_redirects=False)


def test_ask_smoke():
    r = client.post("/ask", json={"user": "frog", "question": "What is Tobyworld?"})
    assert r.status_code == 200
    j = r.json()
    # current API guarantees only "answer"
    assert "answer" in j
    # future extension: uncomment when "meta" exists
    # assert "meta" in j
    # assert isinstance(j["meta"].get("docs_used"), int)


def test_health_and_diag():
    r = client.get("/health")
    assert r.status_code == 200
    j = r.json()
    assert j.get("ok") is True
    assert "version" in j

    r = client.get("/diag")
    assert r.status_code == 200
    assert "recent" in r.json()


def test_root_redirects_to_docs():
    r = client.get("/")  # no extra kwargs needed
    # FastAPI normally redirects "/" → "/docs"
    assert r.status_code in (301, 302, 303, 307, 308)
    assert "/docs" in r.headers.get("location", "")
