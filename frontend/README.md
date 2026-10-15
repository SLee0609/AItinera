# AItinera frontend

React + TypeScript + Vite, styled with Tailwind CSS v4. The map uses the Google Maps JavaScript API through `@vis.gl/react-google-maps`.

## Run locally

```sh
cd frontend
npm install
cp .env.example .env.local   # then add your Google Maps API key
npm run dev                  # http://localhost:5173
```

In development the app uses a built-in Paris sample (`VITE_USE_MOCK_API=true` in `.env.development`), so it works before the backend exists. To call the FastAPI backend instead, set `VITE_USE_MOCK_API=false` in `.env.development.local`. Requests to `/api` are proxied to `http://localhost:8000`.

| Variable | Purpose |
| --- | --- |
| `VITE_GOOGLE_MAPS_API_KEY` | Maps JavaScript API key. Without it, the map view shows a setup message and the list view still works. |
| `VITE_GOOGLE_MAPS_MAP_ID` | Map ID for Advanced Markers and cloud styling. Defaults to `DEMO_MAP_ID`. |
| `VITE_API_BASE_URL` | Backend origin, if it isn't served from the same origin under `/api`. |
| `VITE_USE_MOCK_API` | `true` to use the sample itinerary instead of the backend. |

## Scripts

- `npm run dev` starts the dev server.
- `npm run build` type-checks and builds to `dist/`.
- `npm test` runs the unit tests (Vitest).

## Backend contract

`POST /api/itinerary` with `{ "city": "Paris", "days": 3 }` returns an `Itinerary` (see `src/types.ts`) in camelCase. Errors should use FastAPI's `{ "detail": "message" }` shape; the message is shown to the user.

## Layout

- `src/pages/LandingPage.tsx`: destination and trip-length form, example trips, "How it works" and "Examples" dialogs.
- `src/pages/TripPage.tsx`: fetches the itinerary from `/trip?city=…&days=…&view=list|map` and handles loading and errors.
- `src/components/ListView.tsx`, `MapView.tsx`, `ItineraryMap.tsx`: the two results views.
- `src/api/`: API client and the development sample.
