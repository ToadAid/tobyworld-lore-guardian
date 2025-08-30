# 🪞 Tobyworld Lore Guardian — Mirror V3

> Modular, adaptive Lore Guardian for Tobyworld.
> Core traits: **Lucidity / Resonance / Learning / Ledger**.

## Quickstart

```bash
git clone https://github.com/ToadAid/tobyworld-lore-guardian.git
cd tobyworld-lore-guardian

python -m venv .venv && . .venv/bin/activate
pip install -e .[dev]

uvicorn tobyworld.api.server:app --reload --port 8080
```

- GET `/health` → `{ok:true}`
- POST `/ask` → responds with skeleton answer

## Builders' Challenge

Mirror V3 is not just a foundation — it is a dojo.
Every commit is 功德, every PR leaves a mark.

- [PLAN_V3.md](./PLAN_V3.md)
- [CONTRIBUTING.md](./CONTRIBUTING.md)

## License
MIT
