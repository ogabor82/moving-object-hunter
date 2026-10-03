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
`POST /api/tracklets/build`, `POST /api/tracklets/{tracklet_id}/identify`,
`GET /api/tracklets/builds/{build_id}/review-ranking`,
`GET /api/frames/presets`, `GET /api/frames/cutout`,
`POST /api/frames/project`
(interactive docs at http://127.0.0.1:8000/docs). The pipeline endpoints
call IRSA and SkyBoT live; a tracklet build downloads one PSF catalog per
frame and can take from seconds to a few minutes.

Frontend (Node 20+), in a second terminal:

```
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — the blink comparator (AS-029). Pick a
validation sequence on the left (default: 48606 1995 DH, POC control); the
three real ZTF frames load from IRSA through the backend. Step with
← / → or the epoch buttons, blink with space / ▶ Blink, and set the speed
with the slider. The dev server proxies `/api` to port 8000.

Display transform (backend `app/services/image_service.py`): per-frame
ZScale + linear 8-bit stretch, north up / east left by flips only (no
resampling); frames are aligned on the requested sky centre (≤ 0.5 px).

Frame loading (AS-029.1): the frames of the frozen validation sequences
take their IRSA metadata from the frozen AS-022 report, so they need no
IRSA metadata lookup. Every cutout that downloaded and rendered is kept as
raw FITS in a local disk cache (`backend/.cache/cutouts/`, override with
`MOH_CUTOUT_CACHE_DIR`; git-ignored, safe to delete). A cached cutout is
rendered by the same code as a fresh one and needs no IRSA call, so cached
sequences blink even while IRSA is down; the `X-Cutout-Cache` response
header says `hit` or `miss`. An uncached cutout during an IRSA outage is
still an error (502). The browser keeps loaded frames in memory for the
session.

Tracklet overlay (AS-030): **Build tracklets** runs the existing pipeline
(`POST /api/tracklets/build`, live IRSA PSF catalogs, experimental default
config) on the sequence's frames; the detections of every tracklet are
projected onto each shown cutout by `POST /api/frames/project` (same WCS and
flips as the displayed pixels, from the cached cutout). The panel lists the
tracklets lying inside the field of view (built ones first, nearest the
centre selected by default), with speed, position angle and fit residuals,
and identifies the selected one with `POST /api/tracklets/{id}/identify`
(live SkyBoT: known / unknown / ambiguous with per-detection residuals; a
SkyBoT failure is shown as an error, never as unknown). The overlay marks
this epoch's detection with an open crosshair, the other epochs with rings,
and the motion with a dashed arrow; toggle it with `o`.

Ranked candidate review (AS-041):
`GET /api/tracklets/builds/{build_id}/review-ranking` returns every
tracklet of a build, the built ones ordered by the validated M1 review
priority (AS-039 frozen, AS-040 USEFUL, PROTECTED), the rejected ones
unranked. The rank is review priority only: M1 is not a classifier, its
score is not a probability or confidence, and no candidate is filtered by
score, rank, mask/flag state, faintness or star proximity. Each candidate
carries its 8 feature values and percentiles, its tracklet and a cutout
`view` for the blink comparator. See `backend/docs/review_ranking.md`;
production-vs-research equivalence evidence is in
`backend/validation/results/as041/`.

Ranked candidate review UI (AS-042, read-only): after **Build tracklets**,
**Review all candidates in M1 order →** opens the build's review queue
(`#review=<build_id>`; any build id kept by the backend can also be typed
under *Review a build*). Left: every ranked candidate in M1 order (rank,
tracklet, review priority, speed / fit) and, separately, the unranked
(rejected) tracklets with their reason. Centre: `Candidate 12 / 437` with
◀ Previous / Next ▶ (`n` / `↓`, `p` / `↑`; `← / →`, space and `o` still
drive the frames) and the same blink comparator and overlay as the
sequences, opened from the candidate's `view`. Right: rank and priority
(labelled review order, not probability or confidence), the 8-input M1
evidence collapsed, the tracklet and detections, and SkyBoT identification
on request. Nothing is filtered or hidden by score; no review labels are
stored.

## Tests

```
cd backend
.venv/bin/python -m pytest -q                       # unit tests
RUN_ZTF_INTEGRATION=1 RUN_SKYBOT_INTEGRATION=1 \
  .venv/bin/python -m pytest -q -m integration       # live IRSA/SkyBoT
cd ../frontend && npm test && npm run build && npm run lint  # vitest, type-check, build, lint
```
