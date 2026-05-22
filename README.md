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

## Roadmap

- ✅ **Phase 1:** Text-mode MVP — LLM persona, self-improving skills loop
- ✅ **Phase 2:** ElevenLabs TTS + Whisper STT — local voice conversations
- ✅ **Polish:** Multi-language ready (PL tested)
- **Phase 3 (next):** Twilio integration — real phone calls
- **Phase 4:** Scheduling, family dashboard, GDPR compliance

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
