# Hermes — Dalsze kroki i co przygotować

Pełna mapa kolejnych funkcji do zaimplementowania, od najprostszych po zaawansowane, wraz z wymaganymi kluczami API i kontami zewnętrznymi.

---

## Stan obecny ✅

| Moduł | Status |
|---|---|
| Text mode + skills loop | ✅ Gotowe |
| Voice mode (ElevenLabs + Whisper) | ✅ Gotowe |
| RODO compliance (consent, audit, withdrawal, review queue) | ✅ Gotowe |
| Twilio outbound (TwiML per-turn, dry-run, AMD) | ✅ Gotowe |
| Anthropic 1h prompt cache | ✅ Gotowe |
| Scheduling (APScheduler cron daemon) | ✅ Gotowe |
| Family dashboard web UI | ✅ Gotowe |
| Testy (146 testów, 0 failing) | ✅ Gotowe |

---

## Następne kroki — posortowane wg wysiłku

### 1. 📧 Email delivery (~2h) — **najwyższy priorytet praktyczny**

Po każdym wywołaniu wyślij raport rodzinny na email kontaktu rodzinnego ze seniora.

**Co zrobić:**
- `src/notifications/email.py` — klasa `EmailSender` z SMTP lub SendGrid
- Hook w `manager.finalize_call` po zapisaniu raportu
- `.env`: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`

**Co przygotować:**
- Gmail: włącz "App Passwords" (konto → Bezpieczeństwo → Hasła aplikacji), generuje hasło 16-znakowe
- LUB SendGrid: darmowe konto (100 maili/dzień), klucz API z poziomu dashboard

---

### 2. 🔄 Migracja na Claude Sonnet + weryfikacja cache (~30 min)

Zamiana modeli na Anthropic żeby faktycznie korzystać z prompt cache i zobaczyć cache hit w logach.

**Co zrobić:**
- Zmień `.env`: `OPERATOR_MODEL=anthropic/claude-sonnet-4`, `SUPERVISOR_MODEL=anthropic/claude-sonnet-4`
- Uruchom jeden dry-run call, sprawdź `usage.cache_creation_input_tokens` w logach
- Opcjonalnie: dodać logowanie `cache_read_input_tokens` żeby widzieć oszczędności

**Co przygotować:**
- OpenRouter: doładuj konto (Anthropic przez OpenRouter ma surcharge ~8%), wystarczy $5
- LUB bezpośredni klucz Anthropic: `ANTHROPIC_API_KEY` + zmiana providera w `base.py`

---

### 3. 🧙 Onboarding wizard CLI (~3h)

Jedna komenda `hermes onboard` która przeprowadza przez cały setup:
1. Wpisz dane seniora (imię, wiek, schorzenia, kontakt)
2. Nagraj/wpisz zgodę werbalną → zapisz `consent.json`
3. Ustaw harmonogram
4. Wyślij testowy email do rodziny
5. Zrób dry-run call żeby sprawdzić konfigurację

**Co przygotować:** nic nowego — wszystkie moduły już istnieją

---

### 4. 🐳 Production hardening (~1 dzień)

Żeby Hermes działał 24/7 bez twojej ingerencji.

**Co zrobić:**
- `Dockerfile` + `docker-compose.yml` (app + scheduler)
- `systemd/hermes-scheduler.service` — unit file dla daemona
- `GET /health` endpoint w dashboard
- Monitoring: logowanie do pliku z rotacją (`logging.handlers.RotatingFileHandler`)

**Co przygotować:**
- VPS: Hetzner CX22 (~4,5€/mies.), DigitalOcean Droplet ($6/mies.), lub Oracle Cloud Free Tier
- Domena (opcjonalna): dla HTTPS — Let's Encrypt

---

### 5. 📞 Inbound calls (~1 dzień)

Senior dzwoni do nas zamiast my do niego — numer Twilio odbiera, TwiML uruchamia ten sam flow.

**Co zrobić:**
- Nowy endpoint `POST /twilio/inbound` w `telephony/server.py`
- Wykrywanie seniora po numerze telefonu (lookup w `SeniorStore`)
- Konfiguracja numeru Twilio: Webhook URL → `https://twój-serwer/twilio/inbound`

**Co przygotować:**
- Twilio: zakupiony numer (~$1/mies.), skonfigurowany webhook

---

### 6. 🌊 Twilio Media Streams — real-time (~1 tydzień)

WebSocket zamiast play/record loop. ~200ms latency. Radykalnie lepszy UX.

**Co zrobić:**
- `telephony/media_stream_handler.py` — async WebSocket handler
- Streaming Whisper (OpenAI real-time API lub `faster-whisper` lokalnie)
- Streaming ElevenLabs (WebSocket TTS)
- Nowe TwiML: `<Stream>` zamiast `<Record>`

**Co przygotować:**
- Publiczne WSS URL (ngrok ma plan $10/mies. z WSS, lub Cloudflare Tunnel za darmo)
- OpenAI Realtime API klucz ALBO GPU dla faster-whisper lokalnie

---

## Podsumowanie: co przygotować teraz

| Funkcja | Konto/Klucz | Koszt |
|---|---|---|
| Email delivery | Gmail App Password LUB SendGrid | Darmowe |
| Claude Sonnet | OpenRouter (już masz?) doładuj $5 | ~$5 |
| Onboarding | Nic nowego | — |
| Produkcja | VPS Hetzner/DO | ~5€/mies. |
| Inbound calls | Twilio numer | ~$1/mies. |
| Real-time voice | ngrok Pro lub Cloudflare | 0–$10/mies. |

**Rekomendacja na start:** Email delivery → Migracja na Claude → Onboarding wizard. W tej kolejności. Twilio realny deployment i real-time voice odkładamy na gdy będzie prawdziwy użytkownik.
