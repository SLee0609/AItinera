# Supabase

AItinera uses Supabase for accounts (Supabase Auth) and for storing itineraries (Postgres). There are two projects: **aitinera-dev** for local development and **aitinera-prod** for production and preview deployments.

- The frontend uses Supabase only to sign in, with the project's **publishable** key.
- The backend does all database reads and writes with the project's **secret** key, which bypasses row level security. RLS is on for every table; `itineraries` and `saved_itineraries` have no policies, so the publishable key can't read them.

## Tables

| Table | What it holds |
| --- | --- |
| `profiles` | One row per user, created by a trigger on sign-up. Google sign-ins fill the name and avatar. |
| `itineraries` | Every itinerary the backend generates, as served (`data`, camelCase JSON). `id` is the 12-character share ID. |
| `saved_itineraries` | A user's saved itineraries: `(user_id, itinerary_id, saved_at)`. |

The schema is in [`migrations/`](migrations/). Add a new migration file for every change; never edit an applied one.

## Setting up a project

Repeat for both projects.

1. **Create the project** at supabase.com. Security options: **Enable Data API** on (the backend uses it), **Automatically expose new tables** off (the migration grants exactly what's needed), **Enable automatic RLS** on. Under Project Settings → JWT Keys, check that the project uses **asymmetric signing keys** (ECC P-256 or RSA, the default for new projects). The backend verifies tokens against the public keys at `/auth/v1/.well-known/jwks.json` and rejects legacy shared-secret (HS256) tokens.
2. **Apply the migration.** Paste `migrations/*.sql` into the SQL Editor and run it, or use the Supabase CLI:
   ```sh
   supabase init        # once; creates supabase/config.toml and leaves migrations/ alone
   supabase link --project-ref <ref>
   supabase db push
   ```
3. **Auth → URL Configuration:**
   - Site URL: `https://aitinera-app.vercel.app` (prod) or `http://localhost:5173` (dev).
   - Redirect URLs: `https://aitinera-app.vercel.app/**` and your preview deployment pattern (prod); `http://localhost:5173/**` (dev). Sign-in redirects back to the page the user came from, such as `/trip/<id>?save=1`, so the wildcard is required.
4. **Auth → Sign In / Providers:**
   - Email: on, with "Confirm email" on. Set the minimum password length to 8 to match the frontend.
   - Google: create an OAuth client (Web application) in Google Cloud Console with the authorized redirect URI `https://<ref>.supabase.co/auth/v1/callback`, then paste its client ID and secret here.
5. **Keys** (Project Settings → API Keys), stored in Vercel:

   | Vercel project | Variable | Value |
   | --- | --- | --- |
   | `aitinera-api` | `SUPABASE_URL` | `https://<ref>.supabase.co` |
   | `aitinera-api` | `SUPABASE_SECRET_KEY` | secret key (`sb_secret_…`) |
   | `aitinera` | `VITE_SUPABASE_URL` | `https://<ref>.supabase.co` |
   | `aitinera` | `VITE_SUPABASE_PUBLISHABLE_KEY` | publishable key (`sb_publishable_…`) |

   Prod values go in Production and Preview (`SUPABASE_SECRET_KEY` marked Sensitive); dev values go in Development. Then pull them: `vercel env pull .env` in `backend/` and `vercel env pull .env.local` in `frontend/`.

Without these variables the app still works: the backend generates itineraries without IDs, and the frontend hides accounts and disables Share.
