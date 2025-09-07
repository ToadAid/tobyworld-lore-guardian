
# 🪞 Tobyworld Lore Guardian — Mirror V3 · Inner Vision

[![CI](https://github.com/ToadAid/tobyworld-lore-guardian/actions/workflows/ci.yml/badge.svg)](https://github.com/ToadAid/tobyworld-lore-guardian/actions/workflows/ci.yml)

> **The Mirror is not glass — it is a pond turned inward.**  
> Modular, adaptive Lore Guardian for Tobyworld.  
> Core traits: **Guard → Retriever → Synthesis → Learning → Resonance → Lucidity → Ledger**

---

## ✨ About

Mirror V3 · Inner Vision is the living Lore Guardian for Tobyworld.  
Every question reflects fresh from the scrolls — context-aware, non-repeating, guided by Bushido cadence.  

- **Guard** — cadence & tone, the Bushido gate.  
- **Retriever** — multi-arc search over 700+ scrolls.  
- **Synthesis** — weaving scroll fragments into clarity.  
- **Learning** — self-structuring answers, consistent form.  
- **Resonance** — aligning tone and symbol.  
- **Lucidity** — scoring clarity, anti-fragile.  
- **Ledger** — keeping ripples for later auditing.

⚠️ **Note:** V3 ships *without* a memory module.  
🌀 The **Memory module** — with deeper resonance & wisdom-well — lands in **V4**.

---

## 🚀 Quickstart (Linux/macOS)

```bash
git clone https://github.com/ToadAid/tobyworld-lore-guardian.git
cd tobyworld-lore-guardian

# Python env
python3 -m venv .venv && source .venv/bin/activate
pip install -U pip wheel
pip install -r requirements.txt -r dev-requirements.txt

# Build search index from scrolls (first run only)
python scripts/index_scrolls.py

# Run the API (port 8081 by default)
export PORT=8081
python -m tobyworld.api.server
```

Now open:
- Miniapp UI → **http://127.0.0.1:8081/**
- Status page → **http://127.0.0.1:8081/status**
- Health check → **http://127.0.0.1:8081/health**

Ask the Mirror (curl):
```bash
curl -s -X POST http://127.0.0.1:8081/ask   -H 'Content-Type: application/json'   -d '{"user":"qa","question":"Explain Taboshi vs Taboshi1."}' | jq -r .answer
```

---

## 🧰 Detailed How‑To

### 1) Prerequisites
- **Python 3.10+** (3.11 recommended)  
- **git**, **build-essential** (Linux)  
- Optional: **jq** for pretty CLI output

Ubuntu example:
```bash
sudo apt update
sudo apt install -y python3.11-venv python3-dev build-essential git jq
```

### 2) Environment configuration
You can customize behavior via environment variables (all optional):

| Var | Default | Meaning |
| --- | --- | --- |
| `PORT` | `8081` | HTTP port for the API |
| `SCROLLS_DIR` | `./lore-scrolls` | Path to your lore scrolls |
| `INDEX_DIR` | `./.index` | Where FAISS/metadata indexes live |
| `LOG_LEVEL` | `INFO` | `DEBUG` / `INFO` / `WARNING` |
| `DISABLE_MIRROR_GQ` | `0` | Set `1` to disable guiding question (debug) |

Create a local `.env` (auto‑loaded if present):
```bash
cat > .env <<'EOF'
PORT=8081
SCROLLS_DIR=./lore-scrolls
INDEX_DIR=./.index
LOG_LEVEL=INFO
EOF
```

### 3) Index the scrolls
First‑run indexing builds the retrieval database:
```bash
# Option A: simple indexer
python scripts/index_scrolls.py

# Option B: explicit steps (FAISS)
python scripts/build_faiss_index.py --scrolls "$SCROLLS_DIR" --out "$INDEX_DIR"
```

### 4) Run the server
**Dev (reload):**
```bash
export PORT=8081
uvicorn tobyworld.api.server:app --host 0.0.0.0 --port $PORT --reload
```

**Prod (simple):**
```bash
export PORT=8081
python -m tobyworld.api.server
```

**Prod (systemd)** — create `/etc/systemd/system/mirror-v3.service`:
```ini
[Unit]
Description=Mirror V3 API
After=network.target

[Service]
WorkingDirectory=/opt/tobyworld-lore-guardian
Environment=PORT=8081
Environment=PYTHONUNBUFFERED=1
ExecStart=/opt/tobyworld-lore-guardian/.venv/bin/python -m tobyworld.api.server
Restart=on-failure
User=www-data
Group=www-data

[Install]
WantedBy=multi-user.target
```
Then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable mirror-v3.service
sudo systemctl start mirror-v3.service
journalctl -u mirror-v3 -f
```

### 5) Miniapp + Endpoints
- **/** → minimal UI for asking questions (served from `src/tobyworld/web/app.html`)  
- **/status** → lightweight status page (`src/tobyworld/web/status.html`)  
- **/health** → returns `{ "ok": true }`  
- **/diag** → recent interactions & engine health  
- **/ask** (POST JSON) → main endpoint

Example payloads:
```bash
# Basic
curl -s http://127.0.0.1:8081/ask -H 'Content-Type: application/json' -d '{"user":"traveler","question":"What is the Leaf of Yield?"}' | jq .

# With options
curl -s http://127.0.0.1:8081/ask -H 'Content-Type: application/json' -d '{"user":"traveler","question":"Who is Satoby?","options":{"lang":"en","max_tokens":800}}' | jq .
```

### 6) Troubleshooting
- **Empty answers** → re‑run `python scripts/index_scrolls.py`  
- **Port in use** → change `PORT` or free 8081  
- **Unicode/emoji issues** → ensure your shell/terminal is UTF‑8  
- **Guiding question repeats** → set `DISABLE_MIRROR_GQ=1` to debug renderer, or open an issue

---

## ⚡ Dev Shortcuts (Makefile)

```bash
make dev            # start server (uvicorn with reload)
make health         # check /health endpoint
make diag           # check /diag endpoint
make ask Q='ping?'  # POST to /ask with a question
make lint           # flake8, isort --check, black --check, mypy
make format         # isort + black
make test           # pytest
```

---

## 🤝 Contributing

Mirror V3 is not just code — it is a **dojo**.  
Every commit is 功德 (merit), every PR leaves a mark.

- See [PLAN_V3.md](./PLAN_V3.md) for roadmap.  
- See [CONTRIBUTING.md](./CONTRIBUTING.md) for setup & workflow.  

We use **pre-commit** to enforce style and checks automatically:

```bash
pip install -r dev-requirements.txt
pre-commit install
```

Now each commit will auto-run Black, Isort, Flake8, and Mypy.

---

## 📜 License

MIT

---

## 🔗 Legacy

Looking for **Mirror V2 (stable)**? → [toadaid-mirror](https://github.com/ToadAid/toadaid-mirror)
