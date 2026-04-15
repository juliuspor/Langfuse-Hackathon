# Lanz & Precht Daily Briefing Agent

Focused German-language Flask + React web application for a live-style
agent-to-agent news debate flow using ElevenLabs agents and TTS.

## Why this exists

This project came from a real morning routine: making coffee or breakfast while
listening to the news. The reference podcast has exactly the thoughtful,
slightly theatrical German debate energy that makes one topic feel alive, but it
only releases weekly.

This app is the daily version of that ritual. Pick one headline, let two AI
personas argue it out, and get a short live-style podcast briefing while the
coffee is still brewing. It is useful, and it is also a funny little coping
mechanism for wanting that podcast energy every morning.

## Hackathon Judging North Star

This project is intentionally small and demoable, but it is a working
end-to-end application. It is built to be judged on three things:

- Actually works: Flask serves the React app, fetches headlines, streams debate
  turns over SSE, persists transcripts, and optionally serves generated MP3
  audio per turn.
- Fun: the experience feels like a live morning podcast, not a static news
  summary or chatbot answer.
- Agentic / innovative: two AI personas take turns, react to each other's last
  point, share article-grounded context, stream progressively, and can become
  spoken audio through ElevenLabs TTS.

## What this app does

- Starts a debate for a topic with strict turn alternation (`agent_1` -> `agent_2` -> ...).
- Supports German only (`language=de`).
- Streams each completed turn to the browser as a live event.
- Serves a React/Vite news-feed and podcast-style UI from Flask.
- Loads German headlines from GNews through the Flask backend.
- Plays each generated MP3 turn in sequence in the web UI when audio is enabled.
- Stores transcript + metadata in a local JSON file.
- Optionally generates MP3 audio per turn.
- Serves stored debate data and per-turn audio via API.
- Uses selected article context to ground the generated debate.
- Captures ElevenLabs response metadata (request IDs, character usage when returned by headers).

## Judge-Friendly Demo Path

1. Start Flask with `venv/bin/python -m flask --app app:create_app run`.
2. Open `http://127.0.0.1:5000/`.
3. Pick one headline from the news feed.
4. Generate a short 4-turn debate.
5. Watch the turns stream in order while the podcast-style UI stays responsive.
6. If audio is enabled, play the generated turns; if audio fails, the transcript
   still completes with friendly warnings.

The point of the demo is that one morning headline quickly becomes a little
live show.

## Setup

1. Use the repo-local Python virtual environment at `venv/`.
2. Install backend dependencies:

```bash
venv/bin/python -m pip install -r requirements.txt
```

3. Install frontend dependencies:

```bash
(cd frontend && npm install)
```

4. Create env file:

```bash
cp .env.example .env
```

5. Fill required values in `.env`.

## Project layout

- `app.py` creates the Flask app and serves the built React app from `/`.
- `routes/debate.py` exposes debate, live stream, and audio endpoints.
- `routes/news.py` exposes the headlines endpoint.
- `services/` contains debate orchestration, ElevenLabs calls, and news context
  generation.
- `services/news_feed.py` contains the external headline provider.
- `frontend/` contains the React/Vite source app.
- `frontend/src/lib/debateData.ts` contains speaker metadata and shared UI types.
- `frontend/src/lib/api.ts` contains the browser API/SSE integration.
- `static/frontend/` contains generated Vite build assets served by Flask.
- `tests/` contains backend pytest coverage.

## Environment variables

Required:

- `ELEVENLABS_API_KEY`
- `ELEVENLABS_AGENT_1_ID`
- `ELEVENLABS_AGENT_2_ID`
- `NEWS_API_KEY`

Optional tuning:

- `ELEVENLABS_BASE_URL` (default: `https://api.elevenlabs.io`)
- `ELEVENLABS_VOICE_1_ID` / `ELEVENLABS_VOICE_2_ID` (optional voice overrides; by default voices are read from the ElevenLabs agent config)
- `NEWS_PROVIDER` (default: `gnews`)
- `NEWS_COUNTRY` (default: `de`)
- `NEWS_LANGUAGE` (default: `de`)
- `NEWS_CACHE_TTL_SECONDS` (default: `600`)
- `DATABASE_PATH` (default: `data/debates.json`)
- `AUDIO_STORAGE_DIR` (default: `data/audio`)
- `TTS_MODEL_ID` (default: `eleven_flash_v2_5`)
- `TTS_OUTPUT_FORMAT` (default: `mp3_44100_128`)
- `TTS_OPTIMIZE_STREAMING_LATENCY` (0-4, default: `0`)
- `REQUEST_TIMEOUT_SECONDS` (default: `45`)
- `LOG_LEVEL` (default: `INFO`)

## Run

Build the frontend assets served by Flask:

```bash
cd frontend
npm run build
cd ..
```

Start Flask:

```bash
venv/bin/python -m flask --app app:create_app run
```

Open the app:

```text
http://127.0.0.1:5000/
```

Health check:

```bash
curl -s http://127.0.0.1:5000/health
```

### Frontend development

For fast UI iteration, run Flask on port 5000 and the Vite dev server on port
8080 in separate terminals:

```bash
venv/bin/python -m flask --app app:create_app run
```

```bash
cd frontend
npm run dev
```

The Vite dev server proxies `/api` and `/health` to
`http://127.0.0.1:5000`. When you want Flask to serve the latest UI at `/`, run
`npm run build` from `frontend/`.

## API examples

### Get headlines

```bash
curl -s "http://127.0.0.1:5000/api/news/headlines?category=Schlagzeilen&limit=10"
```

This endpoint uses `NEWS_API_KEY` with the default `gnews` provider.

### Start debate

```bash
curl -s -X POST http://127.0.0.1:5000/api/debate/start \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Soll Deutschland ein Tempolimit einfuehren?",
    "turns": 4,
    "language": "de",
    "include_audio": true,
    "article_source": "Nachrichtenquelle",
    "article_teaser": "Kurzbeschreibung der Meldung.",
    "article_url": "https://example.com/article",
    "article_published_at": "2026-04-15T08:00:00Z"
  }'
```

Sample response:

```json
{
  "conversation_id": "a9b7f40c-2d1f-49d7-9fbf-e0f8f074d7a3",
  "topic": "Soll Deutschland ein Tempolimit einfuehren?",
  "status": "completed",
  "turns": [
    {
      "turn_index": 1,
      "speaker": "agent_1",
      "text": "...",
      "audio_url": "/api/debate/a9b7f40c-2d1f-49d7-9fbf-e0f8f074d7a3/audio/1.mp3"
    }
  ],
  "meta": {
    "request_id": "...",
    "include_audio": true,
    "news_context": {
      "source": "news_article",
      "headline": "Soll Deutschland ein Tempolimit einfuehren?",
      "context": "..."
    },
    "warnings": [],
    "status": "completed",
    "total_turns": 4
  }
}
```

### Live debate stream

The browser UI uses this endpoint to receive turns as soon as they are generated:

```bash
curl -N "http://127.0.0.1:5000/api/debate/live?topic=Soll%20Deutschland%20ein%20Tempolimit%20einfuehren%3F&turns=4&language=de&include_audio=true"
```

When `turns` is omitted, debate endpoints default to 4 turns.

Event order:

```text
connected -> conversation -> turn -> turn -> ... -> completed
```

The debate endpoints also accept optional article context fields:
`article_url`, `article_source`, `article_teaser`, and
`article_published_at`. The React news feed sends these fields for selected
headlines.

### Get debate

```bash
curl -s http://127.0.0.1:5000/api/debate/<conversation_id>
```

### Get turn audio

```bash
curl -L http://127.0.0.1:5000/api/debate/<conversation_id>/audio/1.mp3 --output turn1.mp3
```

## Tests

```bash
venv/bin/python -m pytest
cd frontend
npm run test
npm run lint
npm run build
```

`npm run lint` currently allows a handful of shadcn fast-refresh warnings from
generated UI helpers, but should not report errors.

## Known limitations

- Free news-provider plans can return delayed articles; use a paid or trial
  provider plan if the demo needs real-time headlines.
- Live generation is streamed over one HTTP response, not a background job queue.
- No background job queue for long debates.

## Next backend steps

- Add async job mode + status polling for longer debates.
- Add richer article clustering and related stories.
- Add streaming TTS bytes for lower time-to-first-audio.
- Add per-turn quality controls and smarter context compression.
