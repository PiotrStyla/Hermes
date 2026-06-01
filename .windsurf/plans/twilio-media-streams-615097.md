# Twilio Media Streams — real-time voice

Replace the current `<Play>` + `<Record>` loop with a bidirectional WebSocket
(`<Connect><Stream>`) for sub-second turn latency instead of 3–4 s.

---

## Current flow (play/record loop)

```
Operator text → TTS to MP3 file → <Play> → senior hears it
Senior speaks → <Record> → download WAV → Whisper STT → text
                                                          ↓
                                              Operator generates reply
Per-turn latency: 3–4 s (TTS synth + download + STT)
```

## Target flow (Media Streams)

```
WebSocket open ──────────────────────────────────────────────────────
  ↓                                                                  ↑
Streaming TTS (ElevenLabs PCM → μ-law) ──→ Twilio ──→ senior hears   │
                                           │                         │
Senior speaks ──→ Twilio ──→ μ-law → PCM ──→ Streaming STT → text   │
                                                          ↓          │
                                              Operator generates ────┘
Per-turn latency: ~200 ms (no file I/O, no download, streaming throughout)
```

---

## Step 1 — Streaming TTS adapter

**File:** `src/voice/tts.py` (extend `ElevenLabsTTS`)

- Add `stream()` generator method: yields `bytes` chunks (μ-law 8 kHz)
- Use `elevenlabs.client.text_to_speech.convert_as_stream()` → PCM 16 kHz int16
- Resample 16 kHz → 8 kHz, encode to μ-law (Twilio Media Streams format)
- Keep existing `speak()` for local voice mode

## Step 2 — Streaming STT adapter

**File:** `src/voice/stt.py` (extend `WhisperSTT`)

- Add `StreamingSTT` class wrapping Deepgram real-time API (or OpenAI Realtime)
- Accept μ-law 8 kHz chunks, decode to PCM, feed to STT
- Yield partial/interim transcripts as they arrive
- Fallback: buffer all audio, run batch Whisper at end of turn (worse latency but no new API key)

## Step 3 — Media Streams WebSocket endpoint

**File:** `src/telephony/server.py` (new endpoint)

- `WS /twilio/stream/{call_id}` — Twilio connects here after `<Connect><Stream>`
- Handles Twilio's Media Streams protocol:
  - Inbound `media` messages: μ-law audio chunks → feed to StreamingSTT
  - Outbound `media` messages: μ-law audio chunks ← from StreamingTTS
  - `start`/`stop`/`mark` messages for lifecycle
- Runs the conversation loop: STT partial → operator.generate() → TTS stream → send to Twilio

## Step 4 — Conversation loop for streaming

**File:** `src/telephony/stream_handler.py` (new)

- `StreamingConversation` class — state machine for the WebSocket session
- Interruption handling: if senior starts speaking while operator is mid-sentence,
  stop TTS output, process senior's new utterance
- Withdrawal detection on partial transcripts
- Turn counting, `<<END_CALL>>` detection, hangup
- Post-call: same `finalize_call()` pipeline as current

## Step 5 — TwiML changes

**File:** `src/telephony/turn_handler.py`

- New `_twiml_stream()` helper: `<Connect><Stream url="wss://.../twilio/stream/{id}"/></Connect>`
- `build_initial_turn()` uses `<Stream>` instead of `<Play>` + `<Record>`
- Remove `_twiml_play_then_record()` (keep for fallback)

## Step 6 — Config & env vars

**File:** `src/telephony/config.py`, `.env.example`

- Add `DEEPGRAM_API_KEY` (or `OPENAI_REALTIME_API_KEY`) for streaming STT
- Add `STREAMING_STT_PROVIDER` (deepgram | openai | whisper_batch)
- Add `TWILIO_STREAM_ENABLED` flag (default true, set false to use old play/record)

## Step 7 — Tests

**File:** `tests/test_media_streams.py` (new)

- Mock WebSocket, test message parsing (start/media/stop)
- Test μ-law ↔ PCM conversion round-trip
- Test interruption: incoming audio while TTS is streaming
- Test withdrawal detection on partial transcript
- Test graceful fallback to batch Whisper when Deepgram key missing

---

## Dependencies to add

```
websockets>=13.0       # WebSocket server (or use FastAPI built-in)
deepgram-sdk>=3.0      # streaming STT (optional — falls back to batch Whisper)
```

## Risk: audio format conversion

Twilio Media Streams uses **μ-law 8 kHz**. ElevenLabs outputs **PCM 16 kHz int16**.
We need:

- **TTS path:** PCM 16k → resample to 8k → encode μ-law → Twilio
- **STT path:** Twilio μ-law → decode to PCM 16k → STT engine

Resampling can be done with `scipy.signal.resample` or `numpy` + linear interpolation.
μ-law codec is ~20 lines of Python (or use `audioop` from stdlib).

## Rollback safety

The old `<Play>` + `<Record>` flow stays intact behind `TWILIO_STREAM_ENABLED=false`.
Both paths share the same `finalize_call()` post-call pipeline.
