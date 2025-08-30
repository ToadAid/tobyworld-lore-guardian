from fastapi.testclient import TestClient
from tobyworld.api.server import app

def test_ask_smoke():
    c = TestClient(app)
    r = c.post("/ask", json={"user":"frog","question":"What is Tobyworld?"})
    assert r.status_code == 200
    assert "answer" in r.json()
