# 🪞 Tobyworld Lore Guardian — Mirror V3

[![CI](https://github.com/ToadAid/tobyworld-lore-guardian/actions/workflows/ci.yml/badge.svg)](https://github.com/ToadAid/tobyworld-lore-guardian/actions/workflows/ci.yml)

> Modular, adaptive Lore Guardian for Tobyworld.  
> Core traits: **Lucidity / Resonance / Learning / Ledger**.

---

## Quickstart

Clone and set up a local dev environment:

```bash
git clone https://github.com/ToadAid/tobyworld-lore-guardian.git
cd tobyworld-lore-guardian

python3 -m venv .venv && source .venv/bin/activate
pip install -r dev-requirements.txt

make dev
```

The API will be available on port **8080** by default.

- GET `/health` → `{ "ok": true }`
- GET `/diag`   → recent interactions
- POST `/ask`   → responds with a skeleton answer

---

## Dev Shortcuts

These commands are defined in the `Makefile`:

```bash
make dev            # start server (uvicorn with reload)
make health         # check /health endpoint
make diag           # check /diag endpoint
make ask Q='ping?'  # POST to /ask with a question
make lint           # run flake8, isort --check, black --check, mypy
make format         # auto-format with isort + black
make test           # run pytest
```

---

## Contributing

Mirror V3 is not just a foundation — it is a dojo.  
Every commit is 功德, every PR leaves a mark.

- [PLAN_V3.md](./PLAN_V3.md)
- [CONTRIBUTING.md](./CONTRIBUTING.md)

We use **pre-commit** to enforce style and checks automatically.  
After setup, run:

```bash
pip install -r dev-requirements.txt
pre-commit install
```

Now each commit will auto-run Black, Isort, Flake8, and Mypy.

---

## License

MIT
