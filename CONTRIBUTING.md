# Contributing

Thanks for your interest in Vocal Vantage!

## Dev setup
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env        # AI_MOCK_MODE=true works with no API keys
uvicorn app.main:app --reload
```

## Before opening a PR
- `ruff check app` — lint
- `pytest -q` — tests must pass
- Keep changes focused and documented.

## Notes
- Database schema changes: for this project we use `Base.metadata.create_all`
  on startup. For production-grade migrations, introduce Alembic.
