# frontend

Next.js 14 (App Router, `src/`) + Tailwind + shadcn/ui primitives.

## Phase 4.2 — auth pages + guarded shell

- `src/lib/api.ts` — `apiFetch` with an in-memory access token + automatic
  refresh-on-401
- `src/lib/auth.tsx` — `AuthProvider` / `useAuth` (bootstraps by calling
  `/auth/refresh` on load)
- `src/lib/query.tsx` — TanStack Query provider
- `src/middleware.ts` — redirects `(app)` routes to `/login` when the
  `recruit_refresh` cookie is absent, and away from `/login` when present
- `src/app/(auth)/{login,signup,verify,reset}` — react-hook-form + zod
- `src/app/(app)/layout.tsx` — sidebar shell with a client-side auth guard
- `src/app/(app)/dashboard` — placeholder dashboard

The API is reached through a **same-origin proxy** (`next.config.mjs` rewrites
`/api/*` → `http://localhost:8000`), so the httpOnly refresh cookie is scoped to
the web app and the edge middleware can see it.

## Run

```bash
npm install
npm run dev          # http://localhost:3000  (needs the API on :8000)
# override the API target with API_PROXY_TARGET if the backend isn't on :8000
```

## Build / lint

```bash
npm run build
npm run lint
```
