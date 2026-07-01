# WealthOS

A personal wealth management platform. Built as a monorepo, feature by feature.

```
packages/
  financial-engine/   # pure, dependency-free financial math (xirr, cagr, projection, fire, swp)
apps/
  backend/            # FastAPI HTTP layer over the engine
  frontend/           # Next.js 15 UI
```

The **financial engine** is the heart of the product and is deliberately isolated
from any framework or I/O — it takes plain values in and returns plain values out,
so the math can be tested in isolation and reused across the API, jobs, and reports.

## Current status

A first **vertical slice** is working end to end: a projection (growth) feature
from engine → API → chart.

- `packages/financial-engine` — 5 modules, 85 tests, ~99% coverage.
- `apps/backend` — FastAPI, `POST /api/projection`, 5 API tests.
- `apps/frontend` — Next.js page with a form and a Recharts growth chart.

No auth or database yet; the projection endpoint is stateless.

## Run the slice locally

You need **Python 3.10+** and **Node 18+**. Use two terminals.

### 1. Backend (terminal A)

```bash
cd ~/Documents/WealthOs
pip install -e packages/financial-engine
pip install -e "apps/backend[dev]"
cd apps/backend
uvicorn app.main:app --reload --port 8000
```

Check it: open http://localhost:8000/docs

### 2. Frontend (terminal B)

```bash
cd ~/Documents/WealthOs/apps/frontend
cp .env.local.example .env.local      # points at http://localhost:8000
npm install
npm run dev
```

Open http://localhost:3000, enter your numbers, and hit **Project**. The chart
is computed by the backend using the financial engine.

## Test everything

```bash
# engine
cd packages/financial-engine && pytest

# backend
cd ../../apps/backend && pytest

# frontend (type-check + production build)
cd ../frontend && npm run build
```

## Roadmap (next)

- More engine modules: `inflation`, `goal`, `allocation`, `salary`.
- More API endpoints (FIRE, SWP) + a real dashboard with multiple cards.
- Auth (Clerk) and persistence (Postgres + SQLAlchemy + Alembic) once the
  stack is proven.
