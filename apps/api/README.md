# DegreePilot API

FastAPI backend for DegreePilot. SQLite by default (zero-setup), Postgres optional via `DATABASE_URL`.

## Run locally

```bash
cd apps/api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API: http://localhost:8000  ·  Docs: http://localhost:8000/docs

## Test

```bash
pytest
```
