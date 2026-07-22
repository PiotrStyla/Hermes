# DPIA — Data Protection Impact Assessment

**Wersja:** 1.0
**Data:** 2026-07-22
**Autor:** Compliance & DPO Officer (AI)
**Podstawa prawna:** Art. 35 RODO

---

## 1. Opis przetwarzania

### 1.1 Kontekst
Hermes AI Wellness Call Center wykonuje codzienne automatyczne telefony wellness check-in do osób starszych (65+). Rozmowy są prowadzone przez system AI (LLM), który pyta o samopoczucie, zdrowie, bezpieczeństwo i nastrój. Po każdej rozmowie generowany jest raport dla rodziny seniora.

### 1.2 Zakres danych
- **Dane identyfikacyjne:** imię, wiek, język
- **Dane zdrowotne (Art. 9):** nastrój, ból, leki, wizyty u lekarza, bezpieczeństwo
- **Transkrypcje rozmów:** pełne zapisy treści
- **Dane rodzin:** imiona, kontakty, relacja z seniorem
- **Metadane:** czas rozmów, oceny jakości, logi audytu

### 1.3 Cele przetwarzania
1. Świadczenie usługi wellness check-in (zgoda art. 6(1)(a))
2. Raportowanie dla rodzin (zgoda art. 6(1)(a) + art. 9 explicit)
3. Dokumentowanie opieki (zgoda art. 6(1)(a))
4. Trening AI na danych z rozmów (odrębna zgoda, opcjonalna)

### 1.4 Podmioty przetwarzające
- **Controller:** [do rejestracji — Piotr Styla tymczasowo]
- **Processor:** OpenRouter/OpenAI (LLM API)
- **Odbiorcy:** wyznaczeni członkowie rodziny

---

## 2. Ocena konieczności i proporcjonalności

### 2.1 Konieczność
- Codzienne rozmowy wellness są uzasadnione dla celów opieki nad osobami starszymi
- Generowanie raportów dla rodzin wspiera transparency opieki
- Trening AI na danych jest opcjonalny i wymaga odrębnej zgody

### 2.2 Proporcjonalność
- **Dane zebrane:** minimum niezbędne do celu (imię, wiek, zdrowie)
- **Odbiorcy:** tylko wyznaczeni członkowie rodziny
- **Retencja:** ograniczona czasowo (90 dni - 2 lata)
- **Dostęp:** ograniczony do systemu i rodziny

---

## 3. Ocena ryzyk

| Ryzyko | Severity | Prawdopodobieństwo | Mitigacja |
|--------|----------|-------------------|-----------|
| Nieautoryzowany dostęp do danych zdrowotnych | Wysokie | Niskie | Szyfrowanie, kontrola dostępu, audit log |
| Ujawnienie danych rodzinie bez zgody seniora | Wysokie | Średnie | Explicit consent, consent gates w kodzie |
| Purpose creep (trening AI) | Średnie | Średnie | Odrębna zgoda, opt-out |
| Data breach (OpenRouter) | Wysokie | Niskie | DPA, SCCs, minimalizacja danych |
| Senior nie rozumie zgody | Wysokie | Średnie | Verbally explained, PL language, simple terms |
| Przechowywanie danych indefinite | Średnie | Wysokie | Retention policy, automated purge |
| AI generuje błędne informacje zdrowotne | Średnie | Średnie | Supervisor review, family verification |
| Senior czuje się zmanipulowany przez AI | Średnie | Niskie | No manipulation policy, transparency |
| Wycofanie zgody nie jest honored | Wysokie | Niskie | Consent revoke command, automated purge |

---

## 4. Mitigacje

### 4.1 Techniczne
- ✅ Consent gates w kodzie (ConsentStore)
- ✅ Audit log wszystkich akcji
- ✅ PII redaction (redact_pii)
- ✅ RetentionPolicy (wymaga konfiguracji)
- 🔲 Szyfrowanie danych w spoczynku
- 🔲 DPA z OpenRouter
- 🔲 health_consent default = False

### 4.2 Organizacyjne
- ✅ Privacy policy (wygenerowana)
- ✅ Retention policy (wygenerowana)
- ✅ Art. 9 consent template (wygenerowany)
- 🔲 Rejestracja firmy
- 🔲 Rejestr przetwarzania (Art. 30)
- 🔲 Procedura data breach (72h notification)

### 4.3 Prawne
- 🔲 Umowa powierzenia z OpenRouter (Art. 28)
- 🔲 SCCs dla transfer poza EEA (Art. 46)
- 🔲 Rejestracja controller (Art. 24)

---

## 5. Decyzja

### Czy przetwarzanie jest lawful?
**Warunkowo tak** — po implementacji mitigacji:
1. Naprawa health_consent default → False
2. Rejestracja firmy (controller)
3. DPA z OpenRouter
4. Konfiguracja retention policy
5. Explicit Art. 9 consent dla wszystkich seniorów

### Czy można scaling?
**Nie** — do czasu zakończenia remediacji. Obecny pilot (2 seniorów) jest akceptowalny z wyraźną zgodą, ale scaling wymaga pełnej compliance.

---

## 6. Przegląd

- **Następny przegląd DPIA:** po rejestracji firmy i zawarciu DPA z OpenRouter
- **Trigger do przeglądu:** scaling powyżej 10 seniorów, zmiana modelu AI, nowy processor
- **Owner przeglądu:** DPO Officer

---

*Dokument wygenerowany przez Compliance & DPO Officer (AI) — 2026-07-22*
