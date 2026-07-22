# Rejestr przetwarzania danych osobowych (Art. 30 RODO)

**Wersja:** 1.0
**Data:** 2026-07-22
**Administrator:** [do rejestracji — Piotr Styla tymczasowo]

---

## 1. Działania przetwarzania

### 1.1 Wellness check-in calls

| Pole | Wartość |
|------|---------|
| **Cel** | Codzienne telefony wellness do seniorów |
| **Podstawa prawna** | Zgoda (art. 6 ust. 1 lit. a) |
| **Kategorie danych** | Imię, wiek, język, dane zdrowotne (Art. 9), transkrypcje |
| **Odbiorcy** | Dostawca AI (OpenRouter — processor) |
| **Retencja** | Transkrypcje 90 dni, notatki 1 rok |
| **Transfer poza EOG** | Tak — OpenRouter (USA) — SCCs wymagane |
| **Zabezpieczenia** | Consent gates, audit log, PII redaction |

### 1.2 Raporty rodzinne

| Pole | Wartość |
|------|---------|
| **Cel** | Informowanie rodzin o stanie seniora |
| **Podstawa prawna** | Zgoda (art. 6 ust. 1 lit. a) + explicit Art. 9 |
| **Kategorie danych** | Dane zdrowotne (Art. 9), oceny samopoczucia |
| **Odbiorcy** | Wyznaczeni członkowie rodziny |
| **Retencja** | 2 lata od wygenerowania |
| **Transfer poza EOG** | Nie (lokalne pliki) |
| **Zabezpieczenia** | Consent gates, redact_pii |

### 1.3 Trening AI (self-play + transcripts)

| Pole | Wartość |
|------|---------|
| **Cel** | Ulepszanie systemu AI na podstawie rozmów |
| **Podstawa prawna** | Odrębna zgoda (art. 6 ust. 1 lit. a) — opcjonalna |
| **Kategorie danych** | Transkrypcje rozmów, oceny jakości |
| **Odbiorcy** | Dostawca AI (OpenRouter — processor) |
| **Retencja** | Transkrypcje 90 dni, skill updates bezterminowo (metadane) |
| **Transfer poza EOG** | Tak — OpenRouter (USA) |
| **Zabezpieczenia** | train_on_transcripts scope, opt-out |

### 1.4 Akwizycja klientów (social media)

| Pole | Wartość |
|------|---------|
| **Cel** | Generowanie postów marketingowych |
| **Podstawa prawna** | N/A — wyłącznie dane syntetyczne (self-play) |
| **Kategorie danych** | Brak danych osobowych (dane sztuczne) |
| **Odbiorcy** | Fora, X/LinkedIn (publiczne posty) |
| **Retencja** | Bezterminowo (dane syntetyczne) |
| **Transfer poza EOG** | Nie |
| **Zabezpieczenia** | Brak danych osobowych, brak danych rejestrowych |

### 1.5 Audit log

| Pole | Wartość |
|------|---------|
| **Cel** | Accountability (art. 5(2)) |
| **Podstawa prawna** | Interest public (art. 6 ust. 1 lit. f) |
| **Kategorie danych** | Metadane (actor, action, senior_id, timestamp) |
| **Odbiorcy** | Brak (wewnętrzne) |
| **Retencja** | 3 lata |
| **Transfer poza EOG** | Nie |
| **Zabezpieczenia** | Lokalny plik, kontrola dostępu |

---

## 2. Processors (podmioty przetwarzające)

| Processor | Usługa | Umowa (Art. 28) | Transfer poza EOG | Status |
|-----------|--------|-----------------|-------------------|--------|
| OpenRouter | LLM API | 🔲 Brak DPA | Tak (USA) | Wymaga DPA + SCCs |

---

## 3. Zgody seniorów

| Senior | Scopes | Art. 9 explicit | Język | Status |
|--------|--------|-----------------|-------|--------|
| jadwiga-001 | transcribe, store_transcript, share_with_family, train_on_transcripts | 🔲 Brak | pl | Wymaga Art. 9 |
| stefan-001 | store_transcript, share_with_family | 🔲 Brak | en ❌ | Wymaga Art. 9 + PL + train |

---

*Dokument wygenerowany przez Compliance & DPO Officer (AI) — 2026-07-22*
