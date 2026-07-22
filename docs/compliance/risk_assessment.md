# Ocena ryzyk działalności — Hermes AI Wellness Call Center

**Data:** 2026-07-22
**Autor:** Compliance & DPO Officer (AI)
**Status:** BLOCK — wymagana natychmiastowa remediacja

---

## 1. Podsumowanie werdyktu

Działalność w obecnej formie narusza multiple artykuły RODO/GDPR. Werdykt Compliance Reviewer: **BLOCK**. Operacja nie może lawfully proceed bez remediacji.

---

## 2. Zidentyfikowane ryzyka

### R1. Przetwarzanie danych zdrowotnych bez explicit Art. 9 consent — KRYTYCZNE

- **Artykuł:** Art. 9 RODO
- **Opis:** Dane zdrowotne (nastrój, leki, ból, wizyty u lekarza) są przetwarzane bez wyraźnej, dobrowolnej zgody na kategorię specjalną. `health_consent` domyślnie `True` w kodzie.
- **Ryzyko:** Nielegalne przetwarzanie danych specjalnych. Kary do 20 mln EUR lub 4% obrotu.
- **Remediacja:**
  - Zmienić `health_consent` default na `False`
  - Wymagać explicit opt-in dla danych zdrowotnych
  - Dokumentować zgodę w `consent.json`
  - Wygenerować wzór zgody Art. 9

### R2. Brak zarejestrowanego data controllera — KRYTYCZNE

- **Artykuł:** Art. 5(2), Art. 24 RODO
- **Opis:** Firma nie jest zarejestrowana (brak NIP, KRS, nazwy prawnej). Brak formalnego designation of data controller.
- **Ryzyko:** Brak accountable entity. Niemożliwe egzekwowanie RODO. Kary administracyjne.
- **Remediacja:**
  - Zarejestrować firmę (JDG lub sp. z o.o.)
  - Wyznaczyć data controller
  - Rejestr przetwarzania (Art. 30)

### R3. Brak privacy policy / klauzuli RODO — KRYTYCZNE

- **Artykuł:** Art. 13-14 RODO
- **Opis:** Seniorzy i rodziny nie otrzymują żadnej informacji o przetwarzaniu danych. Brak privacy notice.
- **Ryzyko:** Fundamental transparency failure. Seniorowie nie wiedzą kto, po co i jak długo przetwarza ich dane.
- **Remediacja:**
  - Sporządzić privacy policy w języku polskim, dostosowaną do seniorów
  - Dostarczać przed pierwszą rozmową (verbally + written)
  - Include all mandatory Art. 13/14 information

### R4. Brak umowy powierzenia z OpenRouter — WYSOKIE

- **Artykuł:** Art. 28 RODO
- **Opis:** Dane przesyłane do OpenRouter/OpenAI (external API) bez written data processing agreement. Możliwy transfer poza EEA.
- **Ryzyko:** Nielegalne powierzenie przetwarzania. Brak safeguards dla international transfers.
- **Remediacja:**
  - Zawrzeć DPA (Data Processing Agreement) z OpenRouter
  - Zweryfikować czy OpenRouter jest processor czy joint controller
  - Implement SCCs jeśli dane wychodzą poza EEA
  - Alternatywa: używać modeli hosted w EU

### R5. Brak polityki retencji — ŚREDNIE

- **Artykuł:** Art. 5(1)(e) RODO
- **Opis:** `RetentionPolicy` klasa istnieje w kodzie ale nie jest skonfigurowana. Dane mogą być przechowywane indefinite.
- **Ryzyko:** Przechowywanie danych dłużej niż konieczne.
- **Remediacja:**
  - Zdefiniować retention schedule (transkrypcje 90 dni, notatki zdrowotne 1 rok, raporty 2 lata)
  - Automatyzować usuwanie
  - Udokumentować politykę

### R6. Trening AI na danych z rozmów — ŚREDNIE

- **Artykuł:** Art. 5(1)(b) RODO — Purpose limitation
- **Opis:** `train_on_transcripts` scope może przekraczać original purpose wellness check-ins.
- **Ryzyko:** Purpose creep — dane zebrane dla opieki używane do treningu AI.
- **Remediacja:**
  - Explicit, separate consent dla treningu
  - Clear communication że dane będą użyte do ulepszania AI
  - Opt-out bez wpływu na usługę

### R7. Udostępnianie raportów rodzinom — ŚREDNIE

- **Artykuł:** Art. 7, Art. 9 RODO
- **Opis:** Raporty z danymi zdrowotnymi wysyłane do rodzin. Brak evidence że senior wyraził explicit consent dla sharing health data z konkretnymi członkami rodziny.
- **Ryzyko:** Proxy consent tylko dla legally appointed guardians. Adult senior musi sam zgodzić.
- **Remediacja:**
  - Wymagać explicit consent seniora na sharing z konkretnymi osobami
  - Mechanizm withdrawal
  - Nie polegać na requestach rodziny

### R8. Brak DPIA — WYSOKIE

- **Artykuł:** Art. 35 RODO
- **Opis:** Przetwarzanie danych zdrowotnych vulnerable elderly people jest high-risk. DPIA mandatory.
- **Ryzyko:** Brak DPIA = brak compliance. UODO może nakazać wstrzymanie przetwarzania.
- **Remediacja:**
  - Przeprowadzić DPIA dokumentując ryzyka, mitigacje, necessity
  - Review przed scaling beyond pilot

### R9. Akwizycja przez social media — NISKIE

- **Artykuł:** Art. 5(1)(c) Data minimisation
- **Opis:** Gotowe posty na fora/X/LinkedIn. Ryzyko ujawnienia danych seniorów.
- **Ryzyko:** Minimalne — polityka używa wyłącznie danych z self-play treningów, nie realnych rozmów.
- **Remediacja:**
  - Maintain policy: tylko anonymized training data
  - Brak danych rejestrowych w postach
  - Review przed publikacją

### R10. Brak rejestr przetwarzania (Art. 30) — ŚREDNIE

- **Artykuł:** Art. 30 RODO
- **Opis:** Brak record of processing activities.
- **Ryzyko:** Non-compliance z accountability principle.
- **Remediacja:**
  - Utworzyć rejestr przetwarzania
  - Dokumentować cele, podstawy prawne, odbiorcy, retencja

---

## 3. Macierz ryzyk

| ID | Ryzyko | Artykuł | Severity | Prawdopodobieństwo | Wpływ | Priorytet |
|----|--------|---------|----------|-------------------|-------|-----------|
| R1 | Health data bez Art. 9 consent | Art. 9 | Krytyczne | Wysokie | Kary, wstrzymanie | 1 |
| R2 | Brak data controller | Art. 5(2), 24 | Krytyczne | Wysokie | Kary, brak enforcement | 2 |
| R3 | Brak privacy policy | Art. 13-14 | Krytyczne | Wysokie | Transparency failure | 3 |
| R4 | Brak DPA z OpenRouter | Art. 28 | Wysokie | Średnie | Kary, data breach | 4 |
| R5 | Brak retencji | Art. 5(1)(e) | Średnie | Wysokie | Over-retention | 5 |
| R6 | Purpose limitation trening | Art. 5(1)(b) | Średnie | Średnie | Purpose creep | 6 |
| R7 | Family sharing consent | Art. 7, 9 | Średnie | Średnie | Unlawful sharing | 7 |
| R8 | Brak DPIA | Art. 35 | Wysokie | Wysokie | Wstrzymanie | 8 |
| R9 | Social media akwizycja | Art. 5(1)(c) | Niskie | Niskie | Data leak | 9 |
| R10 | Brak Art. 30 register | Art. 30 | Średnie | Wysokie | Non-compliance | 10 |

---

## 4. Plan remediacji — do końca tygodnia (25.07.2026)

| Zadanie | Owner | Deadline | Status |
|---------|-------|----------|--------|
| Wygenerować privacy policy (PL) | DPO | 23.07 | W toku |
| Wygenerować politykę retencji | DPO | 23.07 | W toku |
| Wygenerować wzór zgody Art. 9 | DPO | 23.07 | W toku |
| Wygenerować checklistę rejestracji | DPO | 23.07 | W toku |
| Naprawić health_consent default | DPO | 22.07 | W toku |
| Naprawić zgodę stefan-001 | DPO | 22.07 | W toku |
| DPIA | DPO | 25.07 | Zaplanowane |
| DPA z OpenRouter | Owner | 25.07 | Wymaga ownera |
| Rejestracja firmy | Owner | 25.07 | Wymaga ownera |
| Rejestr przetwarzania Art. 30 | DPO | 25.07 | Zaplanowane |

---

## 5. Decyzje wymagające właściciela

1. **Rejestracja firmy** — JDG czy sp. z o.o.? Wymaga decyzji i działania właściciela.
2. **DPA z OpenRouter** — skontaktować się z OpenRouter ws. data processing agreement.
3. **Model hosting** — czy rozważyć modele hosted w EU (np. Mistral, Azure EU)?

---

*Dokument wygenerowany przez Compliance & DPO Officer (AI) — 2026-07-22*
