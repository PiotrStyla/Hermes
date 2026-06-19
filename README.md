# Hermes Elderly Care

Prosty opis: to system AI, który codziennie dzwoni do seniora, prowadzi krótką rozmowę wellness, tworzy raport dla rodziny i poprawia jakość kolejnych rozmów.

---

## Spis treści / Table of contents

- [PL: Szybki opis](#pl-szybki-opis)
- [PL: Szybki start](#pl-szybki-start)
- [PL: Najważniejsze komendy](#pl-najwazniejsze-komendy)
- [PL: Jak działa system](#pl-jak-dziala-system)
- [PL: Struktura firmy i etapy zatrudnienia](#pl-struktura-firmy-i-etapy-zatrudnienia)
- [PL: Co zmienia board meeting](#pl-co-zmienia-board-meeting)
- [PL: Zgodność i bezpieczeństwo](#pl-zgodnosc-i-bezpieczenstwo)
- [PL: Najczęstsze problemy](#pl-najczestsze-problemy)
- [EN: Quick overview](#en-quick-overview)
- [EN: Quick start](#en-quick-start)
- [EN: Main commands](#en-main-commands)
- [EN: How the system works](#en-how-the-system-works)
- [EN: Company structure and staffing stages](#en-company-structure-and-staffing-stages)
- [EN: What board meeting changes](#en-what-board-meeting-changes)
- [EN: Compliance and security](#en-compliance-and-security)
- [EN: Troubleshooting](#en-troubleshooting)

---

## PL: Szybki opis

System składa się z kilku agentów AI:

- `Operator` prowadzi rozmowę z seniorem.
- `Supervisor` ocenia jakość rozmowy.
- `Manager` spina cały proces i aktualizuje umiejętności operatora.
- `Report Generator` tworzy raport dla rodziny.
- Warstwa `Company` (CEO, HR, Quality Director, CMO) pilnuje KPI i kierunku firmy.

Główna idea: po każdej rozmowie system uczy się i poprawia następne rozmowy.

## PL: Szybki start

```powershell
# Run from: c:\Users\Hipek\CascadeProjects\windsurf-project-2

# 1) Utwórz i aktywuj virtualenv (jeśli nie masz)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2) Zainstaluj zależności
python -m pip install -r requirements.txt

# 3) Skopiuj konfigurację i ustaw klucz API
copy .env.example .env
# Uzupełnij OPENROUTER_API_KEY w .env

# 4) Sprawdź seniorów
python -m src list-seniors

# 5) Uruchom rozmowę
python -m src call stefan-001

# 6) Sprawdź historię
python -m src view-history stefan-001
```

Po rozmowie sprawdź:

- `data/seniors/<id>/transcripts/`
- `data/seniors/<id>/reports/`
- `data/seniors/<id>/learnings/notes.md`
- `data/skills/operator/`

## PL: Najwazniejsze komendy

```powershell
# Run from: c:\Users\Hipek\CascadeProjects\windsurf-project-2

python -m src list-seniors
python -m src call <senior-id>
python -m src call <senior-id> --voice
python -m src view-history <senior-id>
python -m src company status
python -m src company review
python -m src scheduler start --board-review-hours 24
python -m src dashboard --host 127.0.0.1 --port 8080
```

## PL: Jak dziala system

1. `Manager` ładuje profil seniora i zestaw umiejętności operatora.
2. `Operator` prowadzi rozmowę (tekst, voice lub telephony).
3. Powstaje transkrypt.
4. `Supervisor` ocenia rozmowę: `warmth`, `listening`, `info_quality`, `brevity`.
5. `Manager` może poprawić pliki umiejętności operatora.
6. Powstaje raport dla rodziny.
7. Warstwa `Company` analizuje KPI i ustawia priorytet strategiczny.

## PL: Struktura firmy i etapy zatrudnienia

Aktualny model staffing ma 3 etapy:

- `light` (oszczędny)
- `standard` (domyślny)
- `scale` (rozwój)

Etapy są zapisane w `src/company/state.py` i przechowywane w `data/company/state.json`.

Wspierane role (przykład):

- `CEO`
- `Compliance & DPO Officer`
- `Quality Director`
- `HR Officer`
- `CMO`
- `Manager`
- `Supervisor`
- `Operator`
- `Training Engineer`
- `MLOps/SRE Engineer`
- `Cybersecurity Officer`
- `Księgowy`
- `Customer Success Specialist`

Dodatkowe artefakty biznesowe:

- Macierz odpowiedzialności: `data/company/staffing_raci.md`
- Raport zarządczy: `data/company/reports/board_2026-06-15_10-00.md`

## PL: Co zmienia board meeting

Najwazniejsze zmiany w warstwie `Company` (obowiazuje dla kolejnych zebrań):

- CEO ma teraz osobna sekcje `Agenda 3b` (Innovation Agenda) z 3 torami: `core`, `adjacent`, `moonshot`.
- CEO dostaje kontekst ostatnich dyrektyw, co zmniejsza powtarzanie tych samych decyzji.
- Po `company review` raport markdown zapisuje sie automatycznie do `data/company/reports/board_YYYY-MM-DD_HH-MM.md`.
- Rekomendowany split modeli strategicznych w `.env`:
  - `CEO_MODEL=anthropic/claude-3-5-haiku`
  - `CMO_MODEL=anthropic/claude-3-5-haiku`
  - role operacyjne (np. `SUPERVISOR_MODEL`) pozostaja na szybkim `deepseek/deepseek-v4-flash`.
- Scheduler board meeting jest ustawiony na stala godzine: `10:00 Europe/Warsaw`.

## PL: Zgodnosc i bezpieczenstwo

System ma wbudowane mechanizmy:

- obsługa zgód (`consent`) i ich wycofania,
- retencja i usuwanie danych (`purge`, `forget`),
- redakcja danych wrażliwych,
- kolejka ręcznej weryfikacji (`review-queue`),
- log audytowy (`audit`).

## PL: Najczestsze problemy

1. **`Internal Server Error` na dashboardzie**
   - Upewnij się, że serwer jest uruchomiony na świeżo po zmianach.
   - Sprawdź logi i uruchom ponownie dashboard.

2. **Model LLM zwraca błąd 404/invalid endpoint**
   - Zmień model w `.env` (np. `SUPERVISOR_MODEL`) na działający.

3. **Brak modułów Python**
   - Uruchamiaj komendy przez projektowe `.venv`.

---

## EN: Quick overview

This is an AI system that calls seniors, runs short wellness conversations, writes family reports, and improves itself after each call.

Main agents:

- `Operator`: runs the conversation
- `Supervisor`: scores call quality
- `Manager`: orchestrates and applies improvements
- `Report Generator`: creates family reports
- `Company layer`: CEO/HR/Quality/CMO strategic governance

## EN: Quick start

```powershell
# Run from: c:\Users\Hipek\CascadeProjects\windsurf-project-2

# 1) Create and activate virtualenv (if needed)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2) Install dependencies
python -m pip install -r requirements.txt

# 3) Copy env file and add API key
copy .env.example .env
# Set OPENROUTER_API_KEY in .env

# 4) Check available seniors
python -m src list-seniors

# 5) Run one call
python -m src call stefan-001

# 6) Inspect generated artifacts
python -m src view-history stefan-001
```

## EN: Main commands

```powershell
# Run from: c:\Users\Hipek\CascadeProjects\windsurf-project-2

python -m src list-seniors
python -m src call <senior-id>
python -m src call <senior-id> --voice
python -m src view-history <senior-id>
python -m src company status
python -m src company review
python -m src scheduler start --board-review-hours 24
python -m src dashboard --host 127.0.0.1 --port 8080
```

## EN: How the system works

1. `Manager` loads senior profile and operator skills.
2. `Operator` talks with the senior (text/voice/telephony).
3. Transcript is saved.
4. `Supervisor` evaluates quality (`warmth`, `listening`, `info_quality`, `brevity`).
5. `Manager` updates operator skills when needed.
6. Family report is generated.
7. Company board agents review KPIs and set strategic focus.

## EN: Company structure and staffing stages

The staffing model supports 3 stages:

- `light`
- `standard` (default)
- `scale`

Data locations:

- Runtime state: `data/company/state.json`
- Staffing logic: `src/company/state.py`
- RACI matrix: `data/company/staffing_raci.md`
- Board one-pager: `data/company/reports/board_2026-06-15_10-00.md`

## EN: What board meeting changes

Key updates in the `Company` layer (applies to upcoming meetings):

- CEO now has a dedicated `Agenda 3b` (Innovation Agenda) with 3 tracks: `core`, `adjacent`, `moonshot`.
- CEO now receives recent-directive context, reducing repetitive decisions.
- After `company review`, a markdown board report is auto-saved to `data/company/reports/board_YYYY-MM-DD_HH-MM.md`.
- Recommended strategic model split in `.env`:
  - `CEO_MODEL=anthropic/claude-3-5-haiku`
  - `CMO_MODEL=anthropic/claude-3-5-haiku`
  - operational roles (e.g. `SUPERVISOR_MODEL`) stay on fast `deepseek/deepseek-v4-flash`.
- Board scheduler is configured for fixed time: `10:00 Europe/Warsaw`.

## EN: Compliance and security

Built-in controls include:

- consent management,
- consent withdrawal handling,
- retention and right-to-erasure flows,
- human review queue,
- audit log,
- PII redaction.

## EN: Troubleshooting

1. **Dashboard shows `Internal Server Error`**
   - Restart the dashboard server.
   - Check server logs for traceback.

2. **LLM model endpoint error**
   - Update model value in `.env` (for example `SUPERVISOR_MODEL`).

3. **Python package missing**
   - Run commands with project `.venv`.

---

## License

MIT
