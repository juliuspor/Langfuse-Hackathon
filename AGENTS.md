# AGENTS.md

Guidance for AI agents working on this Flask/Python hackathon codebase.

## Project Overview

Lanz & Precht Daily Briefing Agent is a simple web MVP that turns one daily
news topic into a short live-style debate between two AI personas, with optional
user call-in.

This is a hackathon project. Keep it small, demoable, and emotionally engaging.
The project is expected to be graded on:

- Whether it actually works
- Whether it is fun

When in doubt, prioritize a strong end-to-end demo over broad product features.

## Project Structure

| Directory/File                  | Purpose                                  | Local Docs  |
| ------------------------------- | ---------------------------------------- | ----------- |
| `app.py`                        | Flask app factory, middleware, errors    | `README.md` |
| `routes/debate.py`              | Debate API endpoints and validation      | -           |
| `services/debate_orchestrator.py` | Debate flow, turn order, storage writes | -           |
| `services/elevenlabs_client.py` | ElevenLabs agent and TTS client          | -           |
| `services/news_context.py`      | Mock neutral news context generation     | -           |
| `models/storage.py`             | Local persistence for conversations      | -           |
| `utils/config.py`               | Environment loading and settings         | -           |
| `utils/errors.py`               | App-specific exception types             | -           |
| `templates/`                    | Flask-rendered HTML                      | -           |
| `static/`                       | Browser JavaScript and CSS               | -           |
| `tests/`                        | Pytest coverage for MVP behavior         | -           |
| `data/`                         | Local generated debate/audio data        | -           |

Read `README.md` before changing the run flow, environment variables, API
shape, or demo behavior.

## Build Commands

```bash
# Setup
venv/bin/python -m pip install -r requirements.txt
cp .env.example .env

# Development
venv/bin/python -m flask --app app:create_app run

# Testing
venv/bin/python -m pytest
venv/bin/python -m pytest tests/test_validation.py
venv/bin/python -m pytest tests/test_orchestrator.py
venv/bin/python -m pytest tests/test_live_stream.py

# API smoke checks
curl -s http://127.0.0.1:5000/health
curl -N "http://127.0.0.1:5000/api/debate/live?topic=Soll%20Deutschland%20ein%20Tempolimit%20einfuehren%3F&turns=4&language=de&include_audio=false"
```

## Testing in Development

Use the repo-local virtualenv at `venv/` for Python and pytest commands:

```bash
venv/bin/python -m pytest
```

For backend changes, run the focused test file first, then the full suite if the
change touches orchestration, validation, persistence, or error handling.

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

Needed only when `include_audio=true`:

- `ELEVENLABS_VOICE_1_ID`
- `ELEVENLABS_VOICE_2_ID`

Useful local overrides:

```bash
DATABASE_PATH=data/debates.json
AUDIO_STORAGE_DIR=data/audio
MAX_TURNS=20
LOG_LEVEL=DEBUG
```

Never commit `.env`, API keys, generated credentials, or secret values in code,
tests, docs, commit messages, or PR text.

## Running the Demo Flow

Always optimize for one crisp path:

1. Start the Flask app.
2. Open `http://127.0.0.1:5000/`.
3. Enter one timely news topic.
4. Generate a short debate of 4-8 turns.
5. Confirm the UI streams turns in order and remains responsive.
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
curl -N "http://127.0.0.1:5000/api/debate/live?topic=Test&turns=4&language=de&include_audio=false"
```

If audio files cannot be served, verify the stored path is inside
`AUDIO_STORAGE_DIR`. `routes/debate.py` intentionally rejects paths outside that
directory.

Generated debate data lives under `data/`. Do not delete local data unless the
user explicitly asks or it is necessary for a test setup.

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
- Keep frontend code mobile-friendly and demo-first.
- Avoid adding dependencies unless they clearly improve the demo.

## Product Guidelines

- The MVP should make one topic feel alive quickly.
- Default to German debate behavior unless a task says otherwise.
- Favor short, punchy turns over long essays.
- Protect the live-style illusion: show progress, stream turns, and avoid blank
  waiting states.
- If a feature does not help the demo work or become more fun, defer it.

## Before Writing Code

- Search for existing behavior before adding new code.
- Check `services/debate_orchestrator.py` before changing debate flow.
- Check `routes/debate.py` before changing API inputs or outputs.
- Check `models/storage.py` before changing persistence format.
- Check `static/app.js` and `templates/index.html` before changing UI behavior.
- Add or update tests for validation, orchestration, persistence, and regressions.
- Keep success, error, and warning cases visible in the UI/API where relevant.

## Review Guidelines

- First verify that the main demo path still works.
- Prioritize regressions that break debate generation, live streaming, audio
  playback, or stored conversation retrieval.
- Treat secret exposure, path traversal, unsafe file serving, and accidental
  external calls in tests as high-priority issues.
- Check that validation failures return useful JSON errors.
- Check that new features preserve the "actually works" and "fun" grading
  criteria.
- Do not spend review energy on style-only issues unless they hide a bug.

## Additional Documentation

Read these when relevant:

| Document    | When to Read                                      |
| ----------- | ------------------------------------------------- |
| `README.md` | Setup, environment variables, API examples, tests |
| `.env.example` | Required and optional environment variables    |
