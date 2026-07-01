# WealthOS Backend

FastAPI service. A thin HTTP layer over `packages/financial-engine` — it
validates requests, calls the engine, and maps results (and domain errors) onto
HTTP. No business logic lives here.

## Run locally

From the repo root:

```bash
# 1. Install the engine (editable) so the backend can import it
pip install -e packages/financial-engine

# 2. Install the backend and its dev deps
pip install -e "apps/backend[dev]"

# 3. Start the API
cd apps/backend
uvicorn app.main:app --reload --port 8000
```

Then open http://localhost:8000/docs for the interactive API (Swagger UI).

## Endpoints

- `GET /health` — liveness check.
- `POST /api/projection` — wealth projection. Body:

  ```json
  {
    "principal": 100000,
    "monthly_contribution": 10000,
    "annual_return": 0.12,
    "years": 20,
    "annual_step_up": 0.10
  }
  ```

  Returns the year-by-year series plus `final_value` and `total_contributed`.
  Invalid inputs return `422`.

## Test

```bash
cd apps/backend
pytest
```
