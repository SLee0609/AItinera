# CLAUDE.md

AItinera: web app that generates travel-time-efficient, multi-day itineraries from a city and a trip length (1–7 days). Monorepo with two independently deployed Vercel projects: `frontend/` (React + Vite) and `backend/` (FastAPI). See `README.md` for the overview.

## Commands

Backend (run from `backend/`; always call `.venv/bin/...` directly, because the user's shell has a pyenv-virtualenv prompt hook that deactivates `source .venv/bin/activate`):
- `.venv/bin/uvicorn app.main:app --reload --port 8000`
- `.venv/bin/pytest` · `.venv/bin/ruff check . && .venv/bin/ruff format .` · `.venv/bin/pip-audit -r requirements.txt`

Frontend (run from `frontend/`):
- `npm run dev` (proxies `/api` to `localhost:8000`) · `npm test` · `npm run build` (runs `tsc -b`) · `npm audit`

Run the relevant tests, lint and build after changes.

## API contract

- `POST /api/itinerary` `{city, days}` → `Itinerary`. Every generated itinerary is stored and gets `id`, a 12-character share ID (missing if storing failed).
- `GET /api/itinerary/{id}` → the stored `Itinerary`. Frontend share link: `/trip/:id`.
- `GET /api/saved`, `GET|PUT|DELETE /api/saved/{id}`: the signed-in user's saved itineraries; need `Authorization: Bearer <Supabase access token>`.
- `DELETE /api/account`: deletes the signed-in user. Generated itineraries are kept (`created_by` set null) so share links and other users' saves survive; don't change that cascade.

Response shapes are defined twice and must stay in sync:
- `frontend/src/types.ts` (TypeScript)
- `backend/app/schemas.py` (Pydantic, snake_case fields serialized as camelCase via `alias_generator=to_camel`)

`backend/tests/test_api.py::test_itinerary_shape_matches_frontend_types` and `test_save_list_and_unsave` check the field names; update it with any contract change. Errors are always `{"detail": "<user-facing string>"}`; the frontend displays `detail` verbatim, so write it as a message for end users. Days limits live in `frontend/src/lib/itinerary.ts` and `backend/app/schemas.py`.

## Backend structure

- `app/pipeline.py` orchestrates: Places resolves the city → Gemini suggests `6 × days` candidates → Places verifies `4 × days` → `partition_into_days` → Routes transit times for needed pairs only → `best_order` per day → `fastest_plan` (falls back to the naive baseline days if they travel less) → optional route polylines.
- `app/algorithm/` is pure (no I/O, deterministic, ties broken by index); keep it that way and unit-test it.
- `partition_into_days` minimizes total estimated (straight-line) travel per day. It runs greedy assignment plus local search once per possible first seed and scores days with exact Held-Karp, which is exponential in stops per day. Keep `max_stops_per_day` around 8, or the request's CPU time grows quickly.
- `app/services/` wraps Google APIs; `google_http.py` turns HTTP failures into `UpstreamError` (502). `services/supabase.py` (`Store`) reads and writes Supabase over PostgREST with the secret key, which bypasses RLS, so always filter by user; failures become `StorageError` (503).
- `app/auth.py` verifies Supabase access tokens against the project's JWKS (asymmetric keys only). `current_user` requires one; `optional_user` treats bad tokens as guests.
- Storing happens in `main.py` after `generate_itinerary`, not in the pipeline. Storage failure must never fail generation.
- Domain errors in `app/errors.py` map to status codes and user messages.

## Frontend structure

- Design: "Direction B" (Workbench). Fonts Schibsted Grotesk (display) + Public Sans (body); teal accent `#0F766E`; Tokens are in `src/index.css` (`@theme`).
- `src/pages/LandingPage.tsx`, `src/pages/TripPage.tsx` (`/trip?city=&days=` generates, then replaces the URL with `/trip/:id`), `SharedTripPage.tsx` (`/trip/:id?view=list|map`), `LoginPage.tsx` (`/login?next=&mode=`, including "Forgot password?"), `ResetPasswordPage.tsx` (`/reset-password?next=`, where reset emails land), `SavedPage.tsx` (`/saved`). `src/components/TripScreen.tsx` is the shared trip layout; `ListView.tsx`, `MapView.tsx`, `ItineraryMap.tsx`.
- Supabase in the browser is for sign-in only (`src/lib/supabase.ts`, `src/auth/`); all data goes through the backend. Account UI hides itself when `VITE_SUPABASE_*` is unset.
- Guest save flow: Save → `/login?next=/trip/<id>?save=1` → after sign-in (including the email-confirmation and Google redirects) the trip page sees `save=1` and saves. `safeNext` limits `next` to same-site paths.

## Environment and secrets

- `VITE_*` variables are compiled into the browser bundle; never put secrets in them. Backend secrets: `GEMINI_API_KEY`, `GOOGLE_MAPS_SERVER_KEY`, `SUPABASE_SECRET_KEY` (plus `SUPABASE_URL`). Frontend: `VITE_SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_KEY` (public).
- Supabase: separate dev and prod projects. Schema changes are new files in `supabase/migrations/`; never edit an applied one. Setup steps are in `supabase/README.md`.
- Production keys are Sensitive Vercel variables (Production, Preview). Development uses separate keys stored as non-sensitive Development variables, pulled with `vercel env pull .env` (backend; it reads only `.env`) and `vercel env pull .env.local` (frontend). Pulls overwrite the file.
- Don't create `frontend/.env.development`: Vite gives mode-specific files priority over `.env.local`, which silently overrides the developer's values.
- Never read, print or commit `backend/.env` or `frontend/.env.local`.
- The server Maps key must not have website restrictions (server requests send no referrer); it's restricted by API instead.

## Dependencies

- Pin exact versions, choose releases at least two weeks old, and run `npm audit` / `pip-audit` after changes.
- Local Node is 20.18, so the frontend stays on Vite 6 (Vite 7 needs 20.19+) and `@supabase/supabase-js` 2.109.0 (2.110+ needs Node 22).
- Backend runtime deps go in `requirements.txt` (Vercel installs it); dev tools in `requirements-dev.txt`. There's no `pyproject.toml`; tool config is in `pytest.ini` and `ruff.toml`.

## Deployment

- Frontend Vercel project `aitinera` (domain https://aitinera-app.vercel.app): Root Directory `frontend`; `frontend/vercel.json` rewrites `/api/*` to `https://aitinera-api.vercel.app/api/*` and everything else to `index.html`.
- Backend Vercel project `aitinera-api`: Root Directory `backend`, entrypoint `app/main.py`, `maxDuration` 60 s in `backend/vercel.json`.
- Pushing to `main` deploys both. Commit or push only when the user asks.
