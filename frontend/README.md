# Lanz & Precht Frontend

React/Vite frontend for the Flask app.

The app loads headlines from Flask's `/api/news/headlines` endpoint and starts
debates through `/api/debate/live`. Provider secrets stay in the backend
environment.

The product is in German because otherwise the joke would not work lol.

The frontend is staged like a morning podcast player, not a generic dashboard:
choose one headline, start the live debate, and watch the two personas take
turns while audio plays when available. The app expects the Flask backend to
provide headlines, stream text turns, stream a real Fakten-Schiri verdict after
each turn when enabled, and send per-turn audio updates when MP3s are ready.
The frontend should assume the backend is generating real turns through the live
conversation stack, not through mocked transcript filler.

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
`src/lib/api.ts` handles SSE events in the order `connected -> conversation ->
turn -> referee -> audio`.

The shipped UI must not invent demo verdicts locally. If the backend does not
emit `referee` events because the feature is disabled or OpenAI fails, the UI
should show that state honestly rather than rendering mock referee cards.

The shipped demo should also avoid mocked runtime content entirely: live
headlines, live debate turns, live referee verdicts, and live audio when
enabled. If a provider fails, surface the failure honestly instead of swapping
in canned transcript text.

## Frontend best practices

- Keep the main path focused on listening, not configuration.
- Append `turn` updates immediately and merge later `audio` updates into the
  same turn.
- Reflect backend warnings and failures honestly.
- Do not let loading states block the transcript once the first turn exists.
