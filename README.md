# AItinera

**AI-powered efficient travel itineraries. Less backtracking, more exploring.**

AItinera turns a destination and a trip length into a day-by-day sightseeing plan that keeps travel time low. An LLM suggests attractions, Google Maps verifies them and supplies transit times, and the app groups the stops into compact days and orders each day for the shortest route. Each plan shows its total travel time next to the travel time for the same stops in their unoptimized order.

- **Live site:** https://aitinera-app.vercel.app
- **API:** https://aitinera-api.vercel.app (`GET /api/health`)

## How it works

1. **Suggest attractions.** Gemini proposes candidates for the city in priority order, each with a short description, an estimated visit time and its neighborhood.
2. **Verify places.** Google Places matches each candidate to a real place inside the city. Duplicates and unmatched places are dropped and replaced by spare candidates.
3. **Split into days.** Attractions are grouped into days so that the total estimated travel, the shortest straight-line route through each day's stops, is as small as possible, with a cap on each day's sightseeing time. A quick greedy grouping is built from several starting points, then improved by moving and swapping attractions between days.
4. **Get transit times.** Google Routes returns transit times for every pair of stops within a day, plus the pairs the baseline needs. Fetching only these pairs, instead of a full matrix, keeps cost growing linearly with trip length.
5. **Order each day.** Every possible order of a day's stops is compared, and the one with the least travel time is kept.
6. **Compare and present.** The baseline is the same attractions in the LLM's order, cut into consecutive days. The frontend shows the plan as a list or on an interactive map.

## Architecture

```
Browser ──> Vercel: frontend (React + Vite)         Google Maps JavaScript API (map)
               │  /api/* rewrite
               ▼
            Vercel: backend (FastAPI)  ──> Gemini API (attractions)
                                       ──> Places API (New) (verification)
                                       ──> Routes API (transit times, route lines)
```

| | Stack | Folder | Vercel project |
| --- | --- | --- | --- |
| Frontend | React 19, TypeScript, Vite 6, Tailwind CSS v4, `@vis.gl/react-google-maps` | [`frontend/`](frontend/) | `aitinera` (domain `aitinera-app.vercel.app`), Root Directory `frontend` |
| Backend | Python 3.12, FastAPI, httpx, `google-genai` | [`backend/`](backend/) | `aitinera-api`, Root Directory `backend` |

The frontend calls `/api/*` on its own domain, and `frontend/vercel.json` forwards those requests to the backend. In local development, Vite's dev server proxies `/api` to `localhost:8000`.

## Repository layout

```
frontend/   React app: landing page, results list view, results map view
backend/    FastAPI app: POST /api/itinerary and the itinerary algorithm
  app/algorithm/   clustering, ordering, baseline (pure Python, no I/O)
  app/services/    Gemini, Places and Routes clients
```

Each folder has its own README with setup details: [frontend/README.md](frontend/README.md), [backend/README.md](backend/README.md).

## Local development

Prerequisites: Node.js 20+, Python 3.12, the Vercel CLI (`npm i -g vercel`), and access to both Vercel projects. Development API keys are stored in Vercel and pulled into git-ignored env files.

```sh
# Backend (terminal 1)
cd backend
python3.12 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
vercel link                 # choose aitinera-api
vercel env pull .env
.venv/bin/uvicorn app.main:app --reload --port 8000

# Frontend (terminal 2)
cd frontend
npm install
vercel link                 # choose aitinera (the frontend project)
vercel env pull .env.local
npm run dev                 # http://localhost:5173
```

To work on the frontend without the backend, set `VITE_USE_MOCK_API=true` in `frontend/.env.local` to use a built-in Paris sample.

## Tests

```sh
cd backend && .venv/bin/pytest && .venv/bin/ruff check .
cd frontend && npm test && npm run build
```

## API keys

| Key | Used by | Exposure |
| --- | --- | --- |
| `VITE_GOOGLE_MAPS_API_KEY` | Frontend map | Public by design; restricted to the site's domains and the Maps JavaScript API |
| `GEMINI_API_KEY` | Backend | Secret |
| `GOOGLE_MAPS_SERVER_KEY` | Backend | Secret; restricted to Places API (New) and Routes API |

Production keys are Sensitive Vercel variables. Development uses separate keys, stored as Development variables in Vercel.

## Deployment

Both Vercel projects deploy automatically when `main` is pushed; other branches get preview deployments. Environment variables that start with `VITE_` are built into the frontend, so changing one requires a frontend redeploy.

## Cost

Each itinerary request costs roughly **$0.02 + $0.115 × days** at Google's first paid-tier prices, about $0.37 for a 3-day trip. Free monthly allowances cover around 200 three-day trips. Google Cloud quotas, a billing budget alert and a Vercel Firewall rate limit on `/api/itinerary` cap spending.
