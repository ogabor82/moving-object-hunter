# Moving Object Hunter

Searches archival ZTF images for moving point sources, links them into
tracklets and compares them with known solar-system objects (SkyBoT).
Part of the AstroSphera project; specification lives in Notion
(AstroSphera / Asteroid Hunter), tasks in Linear (Gaboro / Moving Object
Hunter).

- `backend/` – Python + FastAPI pipeline and API
- `frontend/` – React + Vite + TypeScript skeleton
- `backend/validation/` – frozen validation set and results (AS-022–AS-024)

Detection/matching thresholds are **experimental defaults**, not
scientifically calibrated. An `unknown` identification is not a discovery.

## Run locally

Backend (Python 3.12+; tested with 3.14):

```
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m uvicorn app.main:app --port 8000
```

API: `GET /api/health`, `GET /api/observations/search`,
`POST /api/tracklets/build`, `POST /api/tracklets/{tracklet_id}/identify`
(interactive docs at http://127.0.0.1:8000/docs). The pipeline endpoints
call IRSA and SkyBoT live; a tracklet build downloads one PSF catalog per
frame and can take from seconds to a few minutes.

Frontend (Node 20+), in a second terminal:

```
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — the page shows whether `/api/health` is
reachable (the dev server proxies `/api` to port 8000).

## Tests

```
cd backend
.venv/bin/python -m pytest -q                       # unit tests
RUN_ZTF_INTEGRATION=1 RUN_SKYBOT_INTEGRATION=1 \
  .venv/bin/python -m pytest -q -m integration       # live IRSA/SkyBoT
cd ../frontend && npm run build && npm run lint      # type-check, build, lint
```
