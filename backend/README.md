# AItinera backend

FastAPI service that turns a city and a trip length into an ordered, day-by-day itinerary. It uses Gemini to suggest attractions and Google Maps Platform (Places API (New), Routes API) to verify them and get transit times. Deployed on Vercel as its own project.

## How an itinerary is built

1. **Suggest**: Gemini lists `6 × days` candidate attractions in priority order, each with a description, visit time and neighborhood (`app/services/gemini.py`).
2. **Verify**: Places resolves the city, then matches candidates in priority order until `4 × days` unique places inside the city area are found. Spares replace rejects (`app/services/places.py`).
3. **Split into days**: farthest-point seeds, then greedy assignment by straight-line distance, capping each day at 1.25× the average sightseeing time and 8 stops (`app/algorithm/clustering.py`). No API calls.
4. **Transit times**: Routes `computeRouteMatrix` (transit, next weekday 10:00 local) for every ordered pair inside each day and the baseline's consecutive pairs only (`app/services/routes.py`). Pairs without a transit route fall back to a walking estimate.
5. **Order each day**: brute force over every order of the day's stops, as an open path (`app/algorithm/ordering.py`).
6. **Baseline**: the same attractions in Gemini's order, cut into consecutive days (`app/algorithm/baseline.py`).
7. **Route lines**: one `computeRoutes` call per leg for the map; failures fall back to straight lines in the frontend.

## Run locally

Requires Python 3.12.

```sh
cd backend
python3.12 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
npm i -g vercel               # once
vercel link                   # once: select the aitinera-api project, not the frontend
vercel env pull .env          # development API keys from Vercel
.venv/bin/uvicorn app.main:app --reload --port 8000
```

Commands call the virtual environment's programs directly (`.venv/bin/...`), so they work without activating it. Activating with `source .venv/bin/activate` also works, unless your shell loads pyenv-virtualenv (`pyenv virtualenv-init`), whose prompt hook deactivates it again right away. Run all commands from `backend/`, where `app.main` and `.env` are found.

```sh
curl -X POST localhost:8000/api/itinerary \
  -H 'Content-Type: application/json' \
  -d '{"city": "Paris", "days": 3}'
```

To use it from the frontend, run `npm run dev` in `frontend/`. Vite proxies `/api` to port 8000.

## Keys

The backend needs two keys. Both are server-only and are never sent to the browser.

| Variable | What it is |
| --- | --- |
| `GEMINI_API_KEY` | Google AI Studio → Get API key, in a Google Cloud project with billing. |
| `GOOGLE_MAPS_SERVER_KEY` | Google Cloud Console → Credentials. No application restriction; API restriction: **Places API (New)** and **Routes API** only. Separate from the frontend's `VITE_GOOGLE_MAPS_API_KEY`. |

Production and development use **different keys**, both stored in the `aitinera-api` Vercel project (Settings → Environment Variables):

| Environment | Sensitive | Used by |
| --- | --- | --- |
| Production, Preview | On (values can't be viewed or pulled) | Deployed backend |
| Development | Off | Local development, through `vercel env pull` |

### Fetching development keys

From `backend/`:

```sh
vercel link          # once per machine; choose the aitinera-api project
vercel env pull .env
```

- Pull into `.env` explicitly: `vercel env pull` writes `.env.local` by default, but the backend reads only `.env`.
- The pull overwrites `.env`. To change a setting such as `GEMINI_MODEL` for everyone, add it to the Development environment in Vercel instead of editing `.env` by hand.
- Restart `uvicorn` after pulling; `--reload` watches code, not `.env`.
- `.env` and `.vercel/` are git-ignored. Extra variables Vercel adds (such as `VERCEL_OIDC_TOKEN`) are ignored by the backend.
- Without access to the Vercel project, copy `.env.example` to `.env` and fill in your own keys.

If a key leaks, regenerate it in Google Cloud or AI Studio, update the value in Vercel, redeploy (production) or pull again (development).

Optional tuning variables and their defaults are listed in `.env.example` and `app/config.py`. `GEMINI_MODEL` defaults to `gemini-3.8-flash`.

## Tests

```sh
.venv/bin/pytest           # algorithm, services (HTTP mocked with respx), API
.venv/bin/ruff check . && .venv/bin/ruff format --check .
.venv/bin/pip-audit -r requirements.txt
```

## API

### `POST /api/itinerary`

Request: `{"city": "Paris", "days": 3}`. `city` is 1–100 characters; `days` is an integer from 1 to 7.

Response `200`: an `Itinerary` in camelCase, matching `frontend/src/types.ts`:

```jsonc
{
  "city": "Paris, France",
  "travelMode": "TRANSIT",
  "optimizedTravelMinutes": 129,
  "naiveTravelMinutes": 226,
  "dayPlans": [
    {
      "day": 1,
      "title": "Champ de Mars & Saint-Germain",
      "travelMinutes": 40,
      "stops": [{ "placeId": "ChIJ…", "name": "Eiffel Tower", "description": "…", "visitMinutes": 120,
                  "location": { "lat": 48.8584, "lng": 2.2945 } }],
      "legs": [{ "durationMinutes": 22, "polyline": "…" }]
    }
  ]
}
```

`legs[i]` goes from `stops[i]` to `stops[i + 1]`. `title` and `polyline` may be missing.

Errors return `{"detail": "<message for the user>"}`:

| Status | Meaning |
| --- | --- |
| 422 | Invalid city or trip length, or not enough verified attractions for the trip |
| 404 | City not found |
| 502 | Gemini or Google Maps request failed |
| 504 | Planning took longer than `PIPELINE_TIMEOUT_S` (55 s) |
| 500 | Keys not configured, or an unexpected error |

### `GET /api/health`

`{"status": "ok"}`. No external calls.

## Deployment

The backend is the Vercel project **aitinera-api**, deployed at https://aitinera-api.vercel.app. It's imported from the same repo as the frontend with **Root Directory** `backend`; Vercel detects FastAPI from `app/main.py` and installs `requirements.txt`. `vercel.json` allows 60 s per request. Pushing to `main` deploys to production.

- Health check: `https://aitinera-api.vercel.app/api/health`.
- The frontend forwards `/api/*` to this URL through a rewrite in `frontend/vercel.json`, so the browser only talks to the frontend's own domain and no CORS setup is needed in production. If the backend URL changes, update that rewrite.

## Cost per request

At first paid-tier prices, after the free monthly allowances: about **$0.02 + $0.115 × days**. That's $0.37 for 3 days and $0.83 for 7 days. Most of it is Place Details and transit matrix elements. The free allowances cover roughly 200 three-day trips a month. To cap spend, set per-API quotas and a budget alert in Google Cloud, and a rate-limit rule for `/api/itinerary` in Vercel Firewall.
