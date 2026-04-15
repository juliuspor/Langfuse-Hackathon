# Lanz & Precht Frontend

React/Vite frontend for the Flask app.

The app loads headlines from Flask's `/api/news/headlines` endpoint and starts
4-turn debates through `/api/debate/live`. Provider secrets stay in the backend
environment.

The frontend is staged like a morning podcast player, not a generic dashboard:
choose one headline, start the live debate, and watch the two personas take
turns while audio plays when available. The app expects the Flask backend to
provide headlines, stream text turns, and send per-turn audio updates when MP3s
are ready.

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

`src/lib/debateData.ts` contains speaker metadata and shared UI types.
