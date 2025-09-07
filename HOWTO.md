
# HOWTO: Install & Run Mirror V3 (8081)

This guide gets you from a fresh clone to a running miniapp at **http://127.0.0.1:8081**.

## 1) Install prerequisites
Ubuntu:
```bash
sudo apt update
sudo apt install -y python3.11-venv python3-dev build-essential git jq
```

macOS (Homebrew):
```bash
brew install python git jq
```

## 2) Clone & env
```bash
git clone https://github.com/ToadAid/tobyworld-lore-guardian.git
cd tobyworld-lore-guardian

python3 -m venv .venv && source .venv/bin/activate
pip install -U pip wheel
pip install -r requirements.txt -r dev-requirements.txt
```

## 3) Configure (optional)
Create `.env` (auto‑loaded):
```bash
cat > .env <<'EOF'
PORT=8081
SCROLLS_DIR=./lore-scrolls
INDEX_DIR=./.index
LOG_LEVEL=INFO
EOF
```

## 4) Build the index
```bash
python scripts/index_scrolls.py
# or: python scripts/build_faiss_index.py --scrolls "$SCROLLS_DIR" --out "$INDEX_DIR"
```

## 5) Run
Dev (hot reload):
```bash
uvicorn tobyworld.api.server:app --host 0.0.0.0 --port 8081 --reload
```

Prod:
```bash
export PORT=8081
python -m tobyworld.api.server
```

Systemd (optional):
create `/etc/systemd/system/mirror-v3.service` as in README, then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable mirror-v3.service
sudo systemctl start mirror-v3.service
```

## 6) Use the miniapp & API
- UI: **http://127.0.0.1:8081/**
- Status: **http://127.0.0.1:8081/status**
- Health: **http://127.0.0.1:8081/health**

Ask (curl):
```bash
curl -s -X POST http://127.0.0.1:8081/ask   -H 'Content-Type: application/json'   -d '{"user":"qa","question":"Explain Taboshi vs Taboshi1."}' | jq -r .answer
```

## Troubleshooting
- Re‑index if you change or add scrolls.  
- Ensure your terminal is UTF‑8 for emoji in output.  
- If the guiding question looks repetitive, export `DISABLE_MIRROR_GQ=1` to debug and open an issue with your payload.
