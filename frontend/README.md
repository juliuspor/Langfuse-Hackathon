# Lanz & Precht Frontend

React/Vite frontend for the Flask demo app.

## Commands

```bash
npm install
npm run dev
npm run build
npm run lint
npm run test
```

The production build writes to `../static/frontend` so Flask can serve it from
`http://127.0.0.1:5000/`.

By default the app calls the Flask API on the same origin. Set
`VITE_API_BASE_URL` only when running the Vite dev server against a separate
backend origin. The Vite dev server proxies `/api` and `/health` to
`http://127.0.0.1:5000`.

The news feed is intentionally mocked in `src/lib/mockData.ts`.
