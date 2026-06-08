# Jak przetestować rozmowę z Hermesem

Masz już skonfigurowanych seniorów — możesz uruchomić pełny cykl rozmowy jedną komendą.

---

## Tryb tekstowy (zalecany na start)

Operator rozmawia z LLM-ową personą Jadwigi. Bez mikrofonu, bez kluczy ElevenLabs/OpenAI.

```powershell
python -m src call jadwiga-001
```

Co zobaczysz w terminalu:
1. Profil seniora ładowany z `data/seniors/jadwiga-001/profile.json`
2. Kolejne tury rozmowy (Operator ↔ Jadwiga, max 18 tur)
3. Oceny Supervisora: warmth / listening / info_quality / brevity (0-10)
4. Zaktualizowane skill-pliki Operatora
5. Raport rodzinny zapisany do `data/seniors/jadwiga-001/reports/`

---

## Tryb głosowy (wymaga mikrofonu + kluczy API)

```powershell
python -m src call jadwiga-001 --voice
```

Wymagane w `.env`:
- `ELEVENLABS_API_KEY` — TTS głos Operatora
- `OPENAI_API_KEY` — Whisper STT (twój mikrofon → tekst)

Operator mówi przez głośniki, Ty odpowiadasz jak senior przez mikrofon.

---

## Po rozmowie

Otwórz dashboard żeby zobaczyć wyniki:
```powershell
python -m src dashboard
```
→ http://127.0.0.1:8080 — karta Jadwigi z wykresem scores

---

## Drugi senior: Stefan

```powershell
python -m src call stefan-001
```

---

## Jeśli brakuje zgody

```powershell
python -m src consent grant jadwiga-001
```
