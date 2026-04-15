# Lanz & Precht Daily Briefing Agent

Minimal German-language Flask web MVP for a live-style agent-to-agent debate flow using ElevenLabs agents and TTS.

## What this app does

- Starts a debate for a topic with strict turn alternation (`agent_1` -> `agent_2` -> ...).
- Supports German only (`language=de`).
- Streams each completed turn to the browser as a live event.
- Plays each generated MP3 turn in sequence in the web UI.
- Stores transcript + metadata in a local JSON file.
- Optionally generates MP3 audio per turn.
- Serves stored debate data and per-turn audio via API.
- Uses a mocked neutral news context generated from the topic.
- Captures ElevenLabs response metadata (request IDs, character usage when returned by headers).

## Setup

1. Use the repo-local Python virtual environment at `venv/`.
2. Install dependencies:

```bash
venv/bin/python -m pip install -r requirements.txt
```

3. Create env file:

```bash
cp .env.example .env
```

4. Fill required values in `.env`.

## Environment variables

Required:

- `ELEVENLABS_API_KEY`
- `ELEVENLABS_AGENT_1_ID`
- `ELEVENLABS_AGENT_2_ID`

Needed for `include_audio=true`:

- `ELEVENLABS_VOICE_1_ID`
- `ELEVENLABS_VOICE_2_ID`

Optional tuning:

- `ELEVENLABS_BASE_URL` (default: `https://api.elevenlabs.io`)
- `DATABASE_PATH` (default: `data/debates.json`)
- `AUDIO_STORAGE_DIR` (default: `data/audio`)
- `TTS_MODEL_ID` (default: `eleven_flash_v2_5`)
- `TTS_OUTPUT_FORMAT` (default: `mp3_44100_128`)
- `TTS_OPTIMIZE_STREAMING_LATENCY` (0-4, default: `0`)
- `REQUEST_TIMEOUT_SECONDS` (default: `45`)
- `LOG_LEVEL` (default: `INFO`)

## Run

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

## API examples

### Start debate

```bash
curl -s -X POST http://127.0.0.1:5000/api/debate/start \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Soll Deutschland ein Tempolimit einfuehren?",
    "turns": 8,
    "language": "de",
    "include_audio": true
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
      "source": "mock",
      "headline": "Mock-Briefing zu Soll Deutschland ein Tempolimit einfuehren?",
      "context": "..."
    },
    "warnings": [],
    "status": "completed",
    "total_turns": 8
  }
}
```

### Live debate stream

The browser UI uses this endpoint to receive turns as soon as they are generated:

```bash
curl -N "http://127.0.0.1:5000/api/debate/live?topic=Soll%20Deutschland%20ein%20Tempolimit%20einfuehren%3F&turns=6&language=de&include_audio=true"
```

Event order:

```text
connected -> conversation -> turn -> turn -> ... -> completed
```

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
```

## Known limitations

- News context is mocked from the topic text (no external news retrieval yet).
- Live generation is streamed over one HTTP response, not a background job queue.
- No background job queue for long debates.

## Next backend steps

- Add async job mode + status polling for longer debates.
- Add optional real news enrichment service.
- Add streaming TTS bytes for lower time-to-first-audio.
- Add per-turn quality controls and smarter context compression.
