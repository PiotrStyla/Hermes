# Hermes — Podsumowanie finansowe i przepływ gotówki

> **Ostatnia aktualizacja:** 2026-08-19 (rev 2 — model Operatora: Claude Sonnet 5)
> **Status:** Aktywny dokument referencyjny
> **Repozytorium:** https://github.com/PiotrStyla/Hermes

---

## 1. Model biznesowy

- **Cena subskrypcji:** 149 PLN/mies./senior (cena rynkowa — równe z opiekunek.pl i eOpiekun.pl)
- **Model:** B2C, dorosłe dzieci płacą za opiekę nad seniorami
- **Brak kosztów kapitałowych** — pełny outsourcing technologiczny

---

## 2. Stack technologiczny i koszty

| Komponent | Provider | Cena |
|-----------|----------|------|
| TTS | ElevenLabs API (Flash/Turbo) | $0.05/1K znaków |
| STT | ElevenLabs Scribe | $0.22/godz. |
| LLM (Operator) | Claude Sonnet 5 (Anthropic) | $2.00/1M in, $10.00/1M out |
| LLM (Supervisor/inni) | GPT-4o-mini (OpenAI) | $0.15/1M in, $0.60/1M out |
| Telefonia | Plivo | $0.027/min (stacjonarne), $0.058/min (komórkowe EEA) |
| Hosting | Railway/Render VPS | ~$15/mies. |
| Email | Mailgun/SendGrid | ~$5/mies. |
| Płatności | Stripe | 2.5% + 1 PLN/transakcja |

**Notatka:** ElevenAgents (gotowa platforma conversational AI od ElevenLabs) rozważona i odrzucona — koszt ~113 PLN/senior vs ~68 PLN/senior w modelu API, brak quality scoring/trening/raportów. Szczegóły w `business_plan.md` sekcja 6.

---

## 3. Koszty na 1 seniora/miesiąc

**Założenia:** 30 rozmów/mies., 7 min/rozmowę, 3 150 znaków TTS/rozmowę, 50% stacjonarne / 50% komórkowe

| Komponent | Koszt (PLN) |
|-----------|-------------|
| ElevenLabs TTS (Flash API) | 19,00 |
| ElevenLabs STT (Scribe) | 1,50 |
| Plivo telefonia (średnia) | 36,00 |
| LLM (Claude Sonnet 5 + GPT-4o-mini) | 7,00 |
| Stripe (płatności) | 4,75 |
| **Razem koszty zmienne** | **68,30 PLN** |

**Marża na seniorze: 149 - 68,30 = 80,70 PLN (54%)**

---

## 4. Koszty stałe (miesięczne)

| Komponent | Koszt (PLN) |
|-----------|-------------|
| Hosting (Railway/Render VPS) | 60 |
| Email (Mailgun/SendGrid) | 20 |
| Plivo numer telefonu | 4 |
| LLM — board meetings + trening (Sonnet 5) | 35 |
| Monitoring/logging | 10 |
| Domena | 1 |
| **Razem** | **~130 PLN/mies.** |

---

## 5. Przepływ gotówki — prognoza 12-miesięczna

**Wyłącznie koszty infrastruktury (bez kosztów zespołu)**

| Miesiąc | Seniorzy | Przychód (PLN) | Koszty zmienne (PLN) | Koszty stałe (PLN) | Przepływ netto (PLN) | Skumulowany (PLN) |
|---------|----------|----------------|----------------------|---------------------|----------------------|-------------------|
| M1 (wrz 2026) | 2 | 298 | 137 | 130 | +31 | 31 |
| M2 (paź 2026) | 3 | 447 | 205 | 130 | +112 | 143 |
| M3 (lis 2026) | 5 | 745 | 342 | 130 | +273 | 416 |
| M4 (gru 2026) | 8 | 1 192 | 546 | 135 | +511 | 927 |
| M5 (sty 2027) | 12 | 1 788 | 820 | 135 | +833 | 1 760 |
| M6 (lut 2027) | 18 | 2 682 | 1 229 | 140 | +1 313 | 3 073 |
| M7 (mar 2027) | 25 | 3 725 | 1 708 | 140 | +1 877 | 4 950 |
| M8 (kwi 2027) | 35 | 5 215 | 2 391 | 145 | +2 679 | 7 629 |
| M9 (maj 2027) | 45 | 6 705 | 3 074 | 145 | +3 486 | 11 115 |
| M10 (cze 2027) | 55 | 8 195 | 3 757 | 150 | +4 288 | 15 403 |
| M11 (lip 2027) | 70 | 10 430 | 4 781 | 150 | +5 499 | 20 902 |
| M12 (sie 2027) | 85 | 12 665 | 5 806 | 155 | +6 704 | 27 606 |

---

## 6. Podsumowanie po 12 miesiącach

| Wskaźnik | Wartość |
|----------|---------|
| Liczba seniorów | 85 |
| Przychód miesięczny | 12 665 PLN |
| Koszty miesięczne | 5 961 PLN |
| Przepływ netto miesięczny | +6 704 PLN |
| Przepływ skumulowany | +27 606 PLN |
| Break-even infrastruktury | Od M1 (pozytywny od pierwszego seniora) |
| Marża na seniorze | 80,70 PLN (54%) |

---

## 7. Analiza wrażliwości marży

| Scenariusz | Cena (PLN) | Koszt/senior (PLN) | Marża/senior (PLN) | Marża % |
|-----------|------------|-------------------|-------------------|---------|
| Bazowy (149, Sonnet 5, Flash TTS, avg telefony) | 149 | 68,30 | 80,70 | 54% |
| Haiku zamiast Sonnet (149, Haiku 4.5) | 149 | 64,50 | 84,50 | 57% |
| Premium (149, Multilingual TTS) | 149 | 87,30 | 61,70 | 41% |
| Tylko komórkowe (149, mobile EEA) | 149 | 76,30 | 72,70 | 49% |
| Promocja -10% (134 PLN) | 134 | 68,30 | 65,70 | 49% |
| Opiekun+ konkurencja (299 PLN) | 299 | 68,30 | 230,70 | 77% |

---

## 8. Konkurencja — ceny i oferta

### Bezpośrednia (AI teleopieka głosowa)

| Usługa | Cena (PLN/mies) | Co oferuje |
|--------|----------------|------------|
| opiekunek.pl — Free | 0 | SMS o lekach, 2 rozmowy/tydz, raport tygodniowy |
| opiekunek.pl — Opiekun | 149 | Codzienne rozmowy (≤15 min), SMS, 2 próby, raport codzienny |
| opiekunek.pl — Opiekun+ | 299 | Codzienne rozmowy (≤30 min), 3 próby, raport codzienny |
| eOpiekun.pl | 149 | Codzienne rozmowy 7 dni/tydz, monitoring leków/wody, raport tygodniowy |

**Zniżki wieloosobowe (opiekunek.pl):** 2 seniorów — 127 PLN/os., 3 — 114 PLN/os., 4 — 104 PLN/os.

### Pośrednia (opaski SOS)

| Usługa | Abonament (PLN/mies) | Sprzęt (jednorazowo) |
|--------|----------------------|---------------------|
| Bezpieczna Rodzina | 69 | 299-649 PLN |
| Senior Alert | 32 (+18 za dodatki) | 200-350 PLN |
| PZU Zdrowie | 78 | 500-800 PLN |
| Teleopieka24 | 45-65 | varies |

### Opieka stacjonarna (referencja)

| Usługa | Cena (PLN/mies) |
|--------|----------------|
| Opiekunka z zamieszkaniem | 6 000-12 000 |
| Prywatny dom opieki | 5 000-15 000 |

---

## 9. Przewaga Hermes vs konkurencja

| Funkcja | opiekunek.pl | eOpiekun.pl | Hermes |
|---------|-------------|-------------|--------|
| Codzienne rozmowy | ✅ ≤15 min | ✅ | ✅ 5+ min (hard block) |
| SMS o lekach | ✅ | ✅ | ❌ (planowane) |
| Raporty dla rodziny | ✅ codzienne | ❌ tygodniowe | ✅ codzienne |
| Health check-in | Basic (leki, woda) | Basic (leki, woda) | Advanced (leki, choroby, ból, sen, apetyt) |
| Safety check | ❌ | ❌ | ✅ (czujniki dymu, upadki, kontakty) |
| Quality scoring (4 osie) | ❌ | ❌ | ✅ |
| Self-play trening | ❌ | ❌ | ✅ (435+ rund) |
| Board meetings (CEO/QD/HR/CMO) | ❌ | ❌ | ✅ |
| Compliance/RODO (Art. 9, DPIA) | ? | ? | ✅ |
| Darmowy plan | ✅ | ✅ (7 dni) | ❌ (planowane) |
| Zniżka wieloosobowa | ✅ | ❌ | ❌ (planowane) |

---

## 10. Modele LLM — porównanie kosztów

| Model | Input $/1M | Output $/1M | Koszt/senior/mies | Trust | DPA/RODO |
|-------|-----------|------------|-----------------|-------|----------|
| GPT-4o-mini (OpenAI) | $0.15 | $0.60 | ~0.43 PLN | Wysoki | ✅ |
| Claude Haiku 4.5 (Anthropic) | $1.00 | $5.00 | ~3.30 PLN | Wysoki | ✅ |
| Claude Sonnet 5 (Anthropic) | $2.00 | $10.00 | ~6.60 PLN | Najwyższy | ✅ |
| GPT-4o (OpenAI) | $2.50 | $10.00 | ~7.20 PLN | Wysoki | ✅ |
| ~~z-ai/glm-5.2~~ (chiński) | ~$0.07 | ~$0.28 | ~0.25 PLN | Niski | Niejasne |

**Rekomendacja (zatwierdzona):** Claude Sonnet 5 (Operator) + GPT-4o-mini (Supervisor). Koszt łącznie ~7 PLN/senior/mies. — pomijalny vs 149 PLN przychodu.

**Wyniki treningu (30 rund, 2026-08-19):**

| Model Operatora | Warmth | Listening | Info Quality | Brevity | Średnia |
|----------------|--------|-----------|-------------|---------|---------|
| Claude Sonnet 5 | 8.1 | 7.8 | **7.3** | 6.7 | **7.48** |
| GPT-4o | 7.9 | 8.3 | 6.2 | 7.4 | 7.45 |
| z-ai/glm-5.2 (chiński) | 8.8 | 8.2 | 6.2 | 8.2 | 7.85 |

Sonnet 5 wybrany mimo nieco niższego brevity — **info_quality 7.3 vs 6.2** (GPT-4o) to kluczowy skok jakościowy. Warmth 8.1 bardzo dobry. Anthropic safety-first — istotne dla danych zdrowotnych.

---

## 11. Kluczowe wnioski

1. **Break-even od pierwszego seniora** (bez kosztów zespołu)
2. **Marża 54%** (80,70 PLN/senior) przy cenie rynkowej 149 PLN
3. **Główne koszty:** telefonia (53% kosztów zmiennych) + TTS (28%) — LLM to 10%
4. **Skumulowany cash po 12 mies.: ~27 600 PLN** — kapitał na decyzje kadrowe
5. **Przy 85 seniorach** przepływ miesięczny (+6 704 PLN) pokrywa 1 etat (~7 000 PLN)
6. **Claude Sonnet 5** (Operator) daje info_quality 7.3 vs 6.2 (GPT-4o) — kluczowa poprawa naszej najsłabszej osi
7. **Hermes oferuje więcej niż konkurencja:** quality scoring, trening, board meetings, advanced health check-in, safety check, compliance

---

*Pełny biznesplan: `docs/business/business_plan.md`*
