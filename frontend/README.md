# AItinera frontend

React + TypeScript + Vite, styled with Tailwind CSS v4. The map uses the Google Maps JavaScript API through `@vis.gl/react-google-maps`. Deployed on Vercel.

## Run locally

Environment variables live in the Vercel project, including its Development environment. Pull them into `.env.local` (git ignores this file):

```sh
cd frontend
npm install
npm i -g vercel        # once
vercel link            # once: select the AItinera frontend project
vercel env pull .env.local
npm run dev            # http://localhost:5173
```

`vercel env pull` overwrites `.env.local`. Run it again whenever a variable changes in Vercel. If you don't have access to the Vercel project, copy `.env.example` to `.env.local` and fill in the values by hand.

By default the dev server calls the backend: requests to `/api` are proxied to `http://localhost:8000`, so start the FastAPI server first (see `backend/README.md`). To use the built-in Paris sample instead, set `VITE_USE_MOCK_API=true` in `.env.local`. Restart `npm run dev` after changing any env file; Vite reads them only at startup.

Don't add a `.env.development` file for this: Vite gives mode-specific files priority over `.env.local`, so its values would override yours.

## Environment variables

All `VITE_` variables are built into the browser bundle, so they are public. None of them is a secret; server-side keys belong to the backend.

| Variable | Purpose | Vercel setup |
| --- | --- | --- |
| `VITE_GOOGLE_MAPS_API_KEY` | Maps JavaScript API key. Without it, the map view shows a setup message and the list view still works. | Production, Preview and Development. Sensitive off. |
| `VITE_GOOGLE_MAPS_MAP_ID` | Map ID from Google Cloud's Map Management, used for Advanced Markers and map styling. Defaults to `DEMO_MAP_ID`, which is only for development. | Production, Preview and Development. Sensitive off. |
| `VITE_USE_MOCK_API` | `true` uses the sample itinerary instead of the backend. | Production, Preview: `true` until the backend is deployed, then `false`. |
| `VITE_API_BASE_URL` | Backend origin, if it isn't served from the same origin under `/api`. | Not set. |

In Vercel, a variable targets either "Production, Preview" or "Development", so a value used in both is added twice. Sensitive variables can't target Development and can't be pulled.

### Google key restrictions

The Maps JavaScript key is restricted in Google Cloud Console:

- **Websites:** `http://localhost:5173/*` and the production URL (`https://<project>.vercel.app/*`). Add new domains here before using them, or the map shows `RefererNotAllowedMapError`. Don't add `https://*.vercel.app/*`, which would allow every Vercel site.
- **APIs:** Maps JavaScript API only.

## Deploying

The Vercel project is connected to the GitHub repo with **Root Directory** set to `frontend` and the Vite preset (`npm run build`, output `dist`). Pushing to `main` deploys to production. Other branches and pull requests get preview deployments.

`VITE_` values are fixed at build time. After changing one in Vercel, redeploy (Deployments → ⋯ → Redeploy) for it to take effect.

`vercel.json` serves `index.html` for every path except `/api/*`, so links such as `/trip?city=Paris&days=3` work on refresh.

## Scripts

- `npm run dev` starts the dev server.
- `npm run build` type-checks and builds to `dist/`.
- `npm run preview` serves the production build locally.
- `npm test` runs the unit tests (Vitest).

## Backend contract

`POST /api/itinerary` with `{ "city": "Paris", "days": 3 }` returns an `Itinerary` (see `src/types.ts`) in camelCase. Errors should use FastAPI's `{ "detail": "message" }` shape; the message is shown to the user.

## Layout

- `src/pages/LandingPage.tsx`: destination and trip-length form, example trips, "How it works" and "Examples" dialogs.
- `src/pages/TripPage.tsx`: fetches the itinerary from `/trip?city=…&days=…&view=list|map` and handles loading and errors.
- `src/components/ListView.tsx`, `MapView.tsx`, `ItineraryMap.tsx`: the two results views.
- `src/api/`: API client and the development sample.
