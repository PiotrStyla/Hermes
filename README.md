# Hermes Elderly Care — Multi-Agent Wellness Call System

A self-improving multi-agent system that conducts daily wellness check-in conversations with elderly people, generates reports for their families, and continuously refines its own conversational skills based on supervisor feedback.

> **MVP Phase 1 — text mode.** The senior is currently played by an LLM persona. Voice (ElevenLabs + Whisper) and real telephony (Twilio) are planned for later phases.

## What it does

Every day, the system:

1. **Calls** a senior (currently text simulation; voice + phone later).
2. **Holds a warm 5-minute conversation** about their mood, health, and safety — never sounding like a script.
3. **Reviews the conversation** with a Supervisor agent that scores warmth, listening, info quality, and brevity.
4. **Improves itself** — the Manager rewrites operator skill files based on supervisor patches, versioning the old ones.
5. **Remembers the senior** — supervisor-flagged details get appended to the senior's `learnings/notes.md` for future calls.
6. **Reports to the family** — a clear, factual markdown report with mood, health notes, conversation highlights, and follow-ups.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    MANAGER (Orchestrator)                     │
│  Loads profile + skills, runs the call, applies supervisor   │
│  patches to skills (with versioning), saves learnings,       │
│  triggers report generation.                                  │
└──────────┬─────────────────────────────────────────┬─────────┘
           │ start                                    │ apply feedback
           ▼                                          │
┌──────────────────────┐    conversation    ┌─────────┴─────────┐
│      OPERATOR        │ ◄────────────────► │  SENIOR PERSONA   │
│  Reads MD skills →   │                    │  LLM playing the  │
│  warm wellness call  │   max 18 turns     │  senior (MVP only)│
└──────────┬───────────┘                    └───────────────────┘
           │ transcript
           ▼
┌──────────────────────┐
│     SUPERVISOR       │ → JSON: scores, issues, skill patches, senior_notes
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│   REPORT GENERATOR   │ → Markdown report for the family
└──────────────────────┘
```

## Quick start

```powershell
# 1. Install
pip install -r requirements.txt

# 2. Configure your OpenRouter API key
copy .env.example .env
# Edit .env and set OPENROUTER_API_KEY

# 3. List the seniors on file
python -m src list-seniors

# 4. Run a full call cycle
python -m src call stefan-001

# 5. Inspect what was created
python -m src view-history stefan-001
```

After a call, look in:
- `data/seniors/<id>/transcripts/` — full conversation
- `data/seniors/<id>/reports/` — report for the family
- `data/seniors/<id>/learnings/notes.md` — accumulated context about this senior
- `data/skills/operator/` — current operator skills (continuously refined)
- `data/skills/operator/_versions/` — historical snapshots of skills before each update

## Project structure

```
src/
├── agents/
│   ├── base.py             # OpenRouter client + retry/rate-limit handling
│   ├── manager.py          # Orchestrates the full cycle, rewrites skills
│   ├── operator.py         # Conducts the call, reads skill markdown files
│   ├── senior_persona.py   # LLM playing the senior (MVP testing only)
│   └── supervisor.py       # Reviews transcript, returns structured JSON
├── conversation/
│   ├── session.py          # Operator ↔ Senior turn loop
│   └── transcript.py       # Markdown formatting
├── seniors/store.py        # Profile / transcripts / reports / learnings I/O
├── skills/
│   ├── loader.py           # Reads operator skill markdown files
│   └── updater.py          # Versions and overwrites skills after a patch
├── reports/generator.py    # Transcript + feedback → family report
├── cli.py                  # argparse entry point
└── __main__.py             # `python -m src ...`

data/
├── seniors/<id>/           # Per-senior data directory
└── skills/operator/        # Markdown skill files (continuously self-updated)
```

## CLI commands

| Command | Description |
|---------|-------------|
| `python -m src call <senior-id>` | Run a full wellness call cycle (text mode) |
| `python -m src call <senior-id> --voice` | Run with ElevenLabs voice + microphone |
| `python -m src list-seniors` | List all seniors on file |
| `python -m src view-history <senior-id>` | Show transcripts and reports for a senior |
| `python -m src view-skills` | List the current operator skills |
| `python -m src consent show <senior-id>` | Show RODO consent state |
| `python -m src consent grant <senior-id>` | Record granted consent |
| `python -m src consent revoke <senior-id>` | Revoke previously granted consent |
| `python -m src purge [--senior-id X] [--dry-run]` | Delete artifacts older than retention policy |
| `python -m src forget <senior-id> [--dry-run] [--yes]` | Right-to-erasure: wipe all data for a senior |
| `python -m src audit [-n N] [--senior-id X]` | Tail the append-only audit log |
| `python -m src compliance-review <file> --kind <kind>` | LLM advisor over an artifact for RODO concerns |
| `python -m src review-queue list [--status pending\|approved\|flagged]` | List human-review entries (AI Act high-risk) |
| `python -m src review-queue show <id>` | Inspect a single review entry |
| `python -m src review-queue approve <id> [--by] [--comment]` | Human approves the report |
| `python -m src review-queue flag <id> [--by] [--comment]` | Human flags the entry for follow-up |
| `python -m src twilio-call <senior-id> [--dry-run]` | Place an outbound wellness call via Twilio |
| `python -m src twilio-serve [--port 8000]` | Run the FastAPI webhook server for Twilio call flow |
| `python -m src twilio-calls [--status ...]` | List staged / live / completed telephony calls |

## Voice mode (Phase 2)

In voice mode the Operator speaks through your speakers using **ElevenLabs TTS**, and **you** play the senior — the system records from your microphone, transcribes with **OpenAI Whisper**, and feeds the text back to the Operator. Everything else (Supervisor review, skill updates, family report) runs identically.

Prerequisites:

1. Install voice dependencies (already in `requirements.txt`):
   ```powershell
   pip install elevenlabs sounddevice numpy
   ```
2. Add API keys to `.env`:
   ```env
   ELEVENLABS_API_KEY=...
   OPENAI_API_KEY=...
   ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM   # optional, default is Rachel
   ```
3. Run:
   ```powershell
   python -m src call jadwiga-001 --voice
   ```

After the Operator finishes speaking, the system listens until you stop talking (~1.6 s of silence). Polish is supported end-to-end (`eleven_multilingual_v2` for TTS, Whisper auto-detects but uses the senior's `language` field).

## Telephony / Real Phone Calls (Phase 3)

The same call cycle, but routed through Twilio's PSTN so the Operator actually phones the senior. Architecture:

1. `twilio-call <senior-id>` stages a `CallState` and asks Twilio (via REST) to dial.
2. When the call connects, Twilio POSTs to `/twilio/start`. We synthesize the disclosure + greeting via ElevenLabs to an MP3, return TwiML with `<Play>` + `<Record>`.
3. After each `<Record>`, Twilio POSTs the recording URL to `/twilio/turn`. We download the WAV, transcribe with Whisper, run the same withdrawal detector + Operator turn loop as in voice mode, return next `<Play>` + `<Record>` (or `<Hangup/>`).
4. `/twilio/status` fires when the call ends and hands the captured history to `ManagerAgent.finalize_call` for the standard review/skill-update/report/review-queue pipeline.

### Setup

1. Install deps:
   ```powershell
   pip install -r requirements.txt
   ```
2. Fill out the Twilio block in `.env` (see `.env.example`): `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`, `TELEPHONY_PUBLIC_URL`.
3. Add `phone_number` (E.164, e.g. `+48123456789`) to the senior's `data/seniors/<id>/profile.json`.
4. In dev, expose your local server publicly via ngrok:
   ```powershell
   ngrok http 8000
   # paste the https URL into TELEPHONY_PUBLIC_URL in .env (no trailing slash)
   ```
5. Run the webhook server in one terminal, place the call in another:
   ```powershell
   python -m src twilio-serve --port 8000
   python -m src twilio-call jadwiga-001
   ```

### Dry-run mode (no Twilio account needed)

If any of the four required env vars is missing, `twilio-call` automatically runs in dry-run: it stages the `CallState`, prints what would have been sent to Twilio, and returns. The webhook server still runs and is testable via `curl` — useful for end-to-end testing of the FastAPI handlers without a real PSTN call.

```powershell
python -m src twilio-call jadwiga-001 --dry-run
```

### Compliance integration

- The pre-call gate is the same as `call`: `consent.status` must be `granted` and required scopes (`transcribe`, `store_transcript`) must be covered.
- If `record_audio` scope is **not** granted, the recorded WAV is deleted from Twilio (REST `DELETE`) and from local disk immediately after Whisper transcription. Only the redacted transcript stays.
- AMD (answering machine detection) prevents talking to a voicemail box — TwiML responds with `<Hangup/>` and the call is audited as `telephony_voicemail_aborted`.
- Webhook signature: every Twilio request is verified against `TWILIO_AUTH_TOKEN` via HMAC-SHA1. In dry-run / dev (no token) verification is skipped with a warning.

### Limitations

- Each turn is a sequential REST round-trip (TwiML → Twilio → Record → webhook → STT → LLM → TTS → TwiML). Latency is ~2-4 s per turn. For lower latency, Phase 3.1 will use Twilio Media Streams + WebSocket.
- Outbound only. Inbound (senior calls us) is not implemented yet.
- Skill updates after a telephony call require `train_on_transcripts` consent, same as text mode.

## Compliance (Phase 2.5 + 2.6)

Built directly against the project's legal analysis (RODO + Prawo Komunikacji Elektronicznej + EU AI Act).

### Pre-call gate

Before any call runs, the Manager checks the senior's consent record. Required scopes by default: `store_transcript`, `share_with_family`; voice mode adds `transcribe`. A `REVOKED` record blocks the call outright. For local development you may pass `--allow-no-consent` to bypass the gate (audited).

```powershell
python -m src consent grant jadwiga-001 --notes "Verbal consent during onboarding"
python -m src call jadwiga-001 --voice
python -m src audit -n 20
```

### Granular scopes

Two extra scopes are deliberately opt-in (not in defaults):

- `process_health_data` — Art. 9 RODO special category; without it, the Operator is instructed not to ask about medications, diagnoses or symptoms.
- `train_on_transcripts` — needed for the self-improving skills loop. Without it, the Manager runs the call but **skips** skill updates after review.

```powershell
python -m src consent grant jadwiga-001 --scope process_health_data --scope train_on_transcripts
```

### Mid-call withdrawal (RODO Art. 7(3))

The session listens for explicit withdrawal phrases in either PL or EN (`wycofuję zgodę`, `koniec rozmowy`, `proszę nie nagrywać`, `stop calling me`, `I withdraw my consent`, ...). A match instantly: (a) revokes consent in storage, (b) audits the event, (c) injects a directive prompting the Operator to deliver a brief warm goodbye and end the call. Deterministic regex — not LLM judgement.

### Pre-call disclosure (RODO Art. 13 + AI Act)

`data/skills/operator/disclosure.md` forces the Operator's first turn to identify itself as an AI, state the call purpose, and remind the senior they can stop at any time. Listed first in the skills `_index.md` and reinforced as a hard rule in the operator system prompt.

### Human-in-the-loop review (AI Act high-risk)

After every call, the Manager decides whether the report needs human review before being treated as final. Flagging rules:

- First 3 calls per senior (onboarding window).
- Any Supervisor score below `QUALITY_THRESHOLD` (default 7).
- Any mid-call consent withdrawal in this call.

Flagged calls land in `data/review_queue/<id>.json` with status `pending`. A human inspects and approves/flags via CLI; both decisions are audited.

```powershell
python -m src review-queue list --status pending
python -m src review-queue show <id>
python -m src review-queue approve <id> --by piotr --comment "Looks good"
```

### Cross-cutting

- Every report saved to disk goes through `redact_pii` (emails, phones, PESEL, IBAN, Polish street addresses).
- Retention is per-senior in `data/seniors/<id>/retention.json`; `purge` enforces it.
- `forget` performs full right-to-erasure for one senior.
- The `ComplianceReviewerAgent` is an LLM **advisor** over artifacts (prompts, reports, code changes). It never enforces anything by itself — the deterministic safeguards above do.

## Roadmap

- ✅ **Phase 1:** Text-mode MVP — LLM persona, self-improving skills loop
- ✅ **Phase 2:** ElevenLabs TTS + Whisper STT — local voice conversations
- ✅ **Polish:** Multi-language ready (PL tested)
- ✅ **Phase 2.5:** Compliance foundations — consent gate, retention, audit log, redaction, RODO reviewer
- ✅ **Phase 2.6:** Disclosure skill, granular scopes (health / training), mid-call withdrawal, human-review queue
- ✅ **Phase 3.0:** Twilio outbound — TwiML `<Play>`/`<Record>` per-turn loop, dry-run mode, AMD, webhook signature verification
- ✅ **Anthropic prompt cache (1h TTL)** — Operator/Supervisor system prompts split into stable + dynamic blocks; cache markers emitted only for `anthropic/*` models, no-op everywhere else
- **Phase 3.1 (next):** Twilio Media Streams (WebSocket, real-time, ~200ms latency)
- **Phase 4:** Scheduling, family dashboard, event bus, inbound calls

## Configuration

Default LLM is `deepseek/deepseek-v4-flash` via OpenRouter. Override per-agent in `.env`:

```env
OPENROUTER_API_KEY=...
DEFAULT_MODEL=deepseek/deepseek-v4-flash
# OPERATOR_MODEL=anthropic/claude-sonnet-4
# SUPERVISOR_MODEL=anthropic/claude-opus-4.6
# MANAGER_MODEL=...
# REPORT_MODEL=...
# SENIOR_PERSONA_MODEL=...
```

## License

MIT
