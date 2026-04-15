# AGENTS.md

Guidance for AI agents working on this Flask/Python + React/Vite hackathon
codebase.

## Project Overview

Lanz & Precht Daily Briefing Agent is a focused German-language web application
that turns one daily news topic into a short live-style debate between two AI
personas, with optional spoken audio.

The intended demo path is fully live. Do not present mocked runtime headlines,
mock transcript turns, mock referee verdicts, or mock audio as if they were
real outputs.

This is a hackathon project. Keep it small, demoable, and emotionally engaging.
The project is expected to be graded on:

- Whether it actually works
- Whether it is fun
- Whether it is agentic / innovative

When in doubt, prioritize a strong end-to-end demo over broad product features.

The product story matters: this is a daily morning-news ritual for someone who
wants the energy of a favorite weekly German debate podcast while making coffee
or breakfast. Keep that personal, slightly funny "daily podcast coping
mechanism" alive in docs, UI copy, and demo flow.

## Project Structure

| Directory/File                  | Purpose                                  | Local Docs  |
| ------------------------------- | ---------------------------------------- | ----------- |
| `app.py`                        | Flask app factory, middleware, errors    | `README.md` |
| `routes/debate.py`              | Debate API endpoints and validation      | -           |
| `routes/news.py`                | Headlines API endpoint                   | -           |
| `services/debate_orchestrator.py` | Debate flow, turn order, storage writes | -           |
| `services/elevenlabs_client.py` | ElevenLabs agent and TTS client          | -           |
| `services/fact_referee.py`      | OpenAI-backed Fakten-Schiri verdicts     | -           |
| `services/news_context.py`      | Article-grounded/fallback news context   | -           |
| `services/news_feed.py`         | External headline provider               | -           |
| `models/storage.py`             | Local persistence for conversations      | -           |
| `utils/config.py`               | Environment loading and settings         | -           |
| `utils/errors.py`               | App-specific exception types             | -           |
| `frontend/`                     | React/Vite source for the browser UI     | `frontend/README.md` |
| `frontend/src/lib/debateData.ts` | Speaker and debate UI metadata          | -           |
| `frontend/src/lib/api.ts`       | Browser API and SSE integration          | -           |
| `static/frontend/`              | Generated frontend build served by Flask | -           |
| `static/`                       | Flask static assets                      | -           |
| `tests/`                        | Pytest coverage for app behavior         | -           |
| `data/`                         | Local generated debate/audio data        | -           |

Read `README.md` before changing the run flow, environment variables, API
shape, or demo behavior.

## Build Commands

```bash
# Setup
venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
cd frontend && npm install

# Development
venv/bin/python -m flask --app app:create_app run
cd frontend && npm run dev

# Testing
venv/bin/python -m pytest
venv/bin/python -m pytest tests/test_validation.py
venv/bin/python -m pytest tests/test_orchestrator.py
venv/bin/python -m pytest tests/test_live_stream.py
cd frontend && npm run test
cd frontend && npm run lint

# Frontend build for Flask
cd frontend && npm run build

# API smoke checks
curl -s http://127.0.0.1:5000/health
curl -N "http://127.0.0.1:5000/api/debate/live?topic=Soll%20Deutschland%20ein%20Tempolimit%20einfuehren%3F&turns=12&language=de&include_audio=false"
```

## Testing in Development

Use the repo-local virtualenv at `venv/` for Python and pytest commands:

```bash
venv/bin/python -m pytest
```

For backend changes, run the focused test file first, then the full suite if the
change touches orchestration, validation, persistence, or error handling.

For frontend changes, use the React/Vite app in `frontend/`:

```bash
cd frontend
npm run test
npm run lint
npm run build
```

`npm run build` writes generated assets to `static/frontend/`, which Flask serves
from `/`. Commit source changes in `frontend/` and the refreshed build output
when the task is to replace or ship the served UI.

For UI/demo-flow changes, manually run the Flask app and test the main browser
flow at:

```text
http://127.0.0.1:5000/
```

Do not assume audio generation is always available during tests. Prefer
`include_audio=false` for cheap smoke checks unless the task explicitly targets
ElevenLabs TTS.

### Using Environment Variables

The repository uses `.env` via `python-dotenv`. Create it from `.env.example`
and fill in secrets locally:

```bash
cp .env.example .env
```

Required for live ElevenLabs calls:

- `ELEVENLABS_API_KEY`
- `ELEVENLABS_AGENT_1_ID`
- `ELEVENLABS_AGENT_2_ID`
- `NEWS_API_KEY`

The React news feed calls Flask's `/api/news/headlines` endpoint, which uses the
configured news provider. Keep provider credentials on the backend only; do not
call news providers directly from browser code.

Useful local overrides:

```bash
ELEVENLABS_VOICE_1_ID=voice_override_for_agent_1
ELEVENLABS_VOICE_2_ID=voice_override_for_agent_2
OPENAI_API_KEY=local_openai_key
FACT_REFEREE_MODEL=gpt-5-mini
FACT_REFEREE_ENABLED=true
NEWS_PROVIDER=gnews
NEWS_API_KEY=local_news_provider_key
NEWS_COUNTRY=de
NEWS_LANGUAGE=de
NEWS_CACHE_TTL_SECONDS=600
DATABASE_PATH=data/debates.json
AUDIO_STORAGE_DIR=data/audio
MAX_TURNS=20
LOG_LEVEL=DEBUG
```

By default, MP3 generation reads each voice from the configured ElevenLabs
agent. Set `ELEVENLABS_VOICE_1_ID` or `ELEVENLABS_VOICE_2_ID` only when testing
a local override.

Never commit `.env`, API keys, generated credentials, or secret values in code,
tests, docs, commit messages, or PR text.

## Running the Demo Flow

Always optimize for one crisp path:

1. Start the Flask app.
2. Open `http://127.0.0.1:5000/`.
3. Pick one headline from the React news feed.
4. Generate a 12-turn debate.
5. Confirm the UI streams turns in order, the Fakten-Schiri verdict card updates
   after each turn, and the player remains responsive.
6. If audio is enabled, confirm each turn has playable audio and failures show
   as non-fatal warnings.

The core experience should feel like a live radio/podcast exchange, not a form
submission that happens to return text.

## Debugging & Troubleshooting

If Flask cannot start, check `.env` first. `utils/config.py` requires the
ElevenLabs API key and both agent IDs when the normal app factory is used.

If tests fail because configuration is missing, inspect the tests before adding
new env requirements. Tests should generally inject settings or fakes rather
than depending on real API keys.

If live streaming appears stuck, test the SSE endpoint directly:

```bash
curl -N "http://127.0.0.1:5000/api/debate/live?topic=Test&turns=12&language=de&include_audio=false"
```

The current happy-path event order is:

```text
connected -> conversation -> turn -> referee -> turn -> referee -> ... -> completed
```

With audio enabled, each referee verdict still lands before the later MP3 update:

```text
connected -> conversation -> turn -> referee -> audio -> ... -> completed
```

If headline retrieval fails, confirm `NEWS_API_KEY` is set and test the endpoint
directly:

```bash
curl -s "http://127.0.0.1:5000/api/news/headlines?category=Schlagzeilen&limit=5"
```

If audio files cannot be served, verify the stored path is inside
`AUDIO_STORAGE_DIR`. `routes/debate.py` intentionally rejects paths outside that
directory.

Generated debate data lives under `data/`. Do not delete local data unless the
user explicitly asks or it is necessary for a test setup.

If Flask serves an old UI, rebuild the frontend:

```bash
cd frontend
npm run build
```

If the Fakten-Schiri is missing in the UI, check `OPENAI_API_KEY`,
`FACT_REFEREE_ENABLED`, and the Flask logs. The runtime feature must use the
real article context and a live OpenAI call when enabled; do not replace it
with canned verdict text or placeholder review cards in the shipped app.

## Git Workflow

- Never commit directly to `main` unless the user explicitly asks.
- Keep hackathon changes small and reviewable.
- Add only files relevant to the task.
- Do not amend, squash, rebase, or force-push unless explicitly requested.
- Before committing, run the relevant tests from `venv/`.

Suggested branch style:

```bash
git checkout -b codex/short-task-name
```

## Code Style Guidelines

- Use straightforward Python 3.11+.
- Keep Flask routes thin; put debate behavior in `services/`.
- Keep validation explicit and user-facing error messages clear.
- Prefer small functions over new abstractions.
- Use dependency injection through `create_app(test_config=...)` for tests.
- Preserve strict turn alternation between `agent_1` and `agent_2`.
- Treat ElevenLabs/network calls as unreliable and surface friendly warnings.
- Treat OpenAI/network referee calls as unreliable and surface friendly warnings.
- Keep frontend code in `frontend/` mobile-friendly and demo-first.
- Keep `static/frontend/` as generated build output; do not hand-edit built
  bundles unless explicitly debugging generated assets.
- Route headline retrieval through Flask; avoid exposing provider keys in the
  React app.
- Avoid adding dependencies unless they clearly improve the demo.

## Product Guidelines

- The app should make one topic feel alive quickly.
- Support German debate behavior only (`language=de`).
- Favor short, punchy turns over long essays, even across the 12-turn default.
- Protect the live-style illusion: show progress, stream turns, and avoid blank
  waiting states.
- Runtime demo behavior must stay grounded in real inputs. Do not ship mock news
  headlines, mock referee verdicts, canned transcript turns, or fake "live"
  progress states outside tests.
- Preserve the judging story: actually works, fun, and agentic / innovative.
- If a feature does not help the demo work, become more fun, or make the
  agentic behavior clearer, defer it.

## Before Writing Code

- Search for existing behavior before adding new code.
- Check `services/debate_orchestrator.py` before changing debate flow.
- Check `services/fact_referee.py` before changing referee verdict behavior.
- Check `routes/debate.py` before changing API inputs or outputs.
- Check `routes/news.py` and `services/news_feed.py` before changing headline
  retrieval.
- Check `models/storage.py` before changing persistence format.
- Check `frontend/src/` before changing UI behavior.
- Check `frontend/src/lib/api.ts` before changing browser/backend contracts.
- Check `frontend/src/lib/debateData.ts` before changing speaker metadata or
  debate UI types.
- Add or update tests for validation, orchestration, persistence, and regressions.
- Keep success, error, and warning cases visible in the UI/API where relevant.

## Review Guidelines

- First verify that the main demo path still works.
- Prioritize regressions that break debate generation, live streaming, audio
  playback, fact-referee verdicts, or stored conversation retrieval.
- Treat secret exposure, path traversal, unsafe file serving, and accidental
  external calls in tests as high-priority issues.
- Check that validation failures return useful JSON errors.
- Check that new features preserve the "actually works", "fun", and
  "agentic / innovative" grading criteria.
- Do not spend review energy on style-only issues unless they hide a bug.

## Additional Documentation

Read these when relevant:

| Document    | When to Read                                      |
| ----------- | ------------------------------------------------- |
| `README.md` | Setup, environment variables, API examples, tests |
| `frontend/README.md` | Frontend commands and Flask build output |
| `.env.example` | Required and optional environment variables    |
