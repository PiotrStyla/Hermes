# Hermes — Podsumowanie finansowe i przepływ gotówki

> **Ostatnia aktualizacja:** 2026-08-19
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
| LLM (Operator) | Claude Haiku 4.5 (Anthropic) | $1.00/1M in, $5.00/1M out |
| LLM (Supervisor/inni) | GPT-4o-mini (OpenAI) | $0.15/1M in, $0.60/1M out |
| Telefonia | Plivo | $0.027/min (stacjonarne), $0.058/min (komórkowe EEA) |
| Hosting | Railway/Render VPS | ~$15/mies. |
| Email | Mailgun/SendGrid | ~$5/mies. |
| Płatności | Stripe | 2.5% + 1 PLN/transakcja |

**Notatka:** ElevenAgents (gotowa platforma conversational AI od ElevenLabs) rozważona i odrzucona — koszt ~113 PLN/senior vs ~66 PLN/senior w modelu API, brak quality scoring/trening/raportów. Szczegóły w `business_plan.md` sekcja 6.

---

## 3. Koszty na 1 seniora/miesiąc

**Założenia:** 30 rozmów/mies., 7 min/rozmowę, 3 150 znaków TTS/rozmowę, 50% stacjonarne / 50% komórkowe

| Komponent | Koszt (PLN) |
|-----------|-------------|
| ElevenLabs TTS (Flash API) | 19,00 |
| ElevenLabs STT (Scribe) | 1,50 |
| Plivo telefonia (średnia) | 36,00 |
| LLM (Claude Haiku 4.5 + GPT-4o-mini) | 3,30 |
| Stripe (płatności) | 4,75 |
| **Razem koszty zmienne** | **64,50 PLN** |

**Marża na seniorze: 149 - 64,50 = 84,50 PLN (57%)**

---

## 4. Koszty stałe (miesięczne)

| Komponent | Koszt (PLN) |
|-----------|-------------|
| Hosting (Railway/Render VPS) | 60 |
| Email (Mailgun/SendGrid) | 20 |
| Plivo numer telefonu | 4 |
| LLM — board meetings + trening | 25 |
| Monitoring/logging | 10 |
| Domena | 1 |
| **Razem** | **~120 PLN/mies.** |

---

## 5. Przepływ gotówki — prognoza 12-miesięczna

**Wyłącznie koszty infrastruktury (bez kosztów zespołu)**

| Miesiąc | Seniorzy | Przychód (PLN) | Koszty zmienne (PLN) | Koszty stałe (PLN) | Przepływ netto (PLN) | Skumulowany (PLN) |
|---------|----------|----------------|----------------------|---------------------|----------------------|-------------------|
| M1 (wrz 2026) | 2 | 298 | 129 | 120 | +49 | 49 |
| M2 (paź 2026) | 3 | 447 | 194 | 120 | +133 | 182 |
| M3 (lis 2026) | 5 | 745 | 323 | 120 | +302 | 484 |
| M4 (gru 2026) | 8 | 1 192 | 516 | 125 | +551 | 1 035 |
| M5 (sty 2027) | 12 | 1 788 | 774 | 125 | +889 | 1 924 |
| M6 (lut 2027) | 18 | 2 682 | 1 161 | 130 | +1 391 | 3 315 |
| M7 (mar 2027) | 25 | 3 725 | 1 613 | 130 | +1 982 | 5 297 |
| M8 (kwi 2027) | 35 | 5 215 | 2 258 | 135 | +2 822 | 8 119 |
| M9 (maj 2027) | 45 | 6 705 | 2 903 | 135 | +3 667 | 11 786 |
| M10 (cze 2027) | 55 | 8 195 | 3 548 | 140 | +4 507 | 16 293 |
| M11 (lip 2027) | 70 | 10 430 | 4 515 | 140 | +5 775 | 22 068 |
| M12 (sie 2027) | 85 | 12 665 | 5 483 | 145 | +7 037 | 29 105 |

---

## 6. Podsumowanie po 12 miesiącach

| Wskaźnik | Wartość |
|----------|---------|
| Liczba seniorów | 85 |
| Przychód miesięczny | 12 665 PLN |
| Koszty miesięczne | 5 628 PLN |
| Przepływ netto miesięczny | +7 037 PLN |
| Przepływ skumulowany | +29 105 PLN |
| Break-even infrastruktury | Od M1 (pozytywny od pierwszego seniora) |
| Marża na seniorze | 84,50 PLN (57%) |

---

## 7. Analiza wrażliwości marży

| Scenariusz | Cena (PLN) | Koszt/senior (PLN) | Marża/senior (PLN) | Marża % |
|-----------|------------|-------------------|-------------------|---------|
| Bazowy (149, Flash TTS, avg telefony) | 149 | 64,50 | 84,50 | 57% |
| Premium (149, Multilingual TTS) | 149 | 83,50 | 65,50 | 44% |
| Tylko komórkowe (149, mobile EEA) | 149 | 72,50 | 76,50 | 51% |
| Promocja -10% (134 PLN) | 134 | 64,50 | 69,50 | 52% |
| Opiekun+ konkurencja (299 PLN) | 299 | 64,50 | 234,50 | 78% |

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

**Rekomendacja:** Claude Haiku 4.5 (Operator) + GPT-4o-mini (Supervisor). Koszt łącznie ~3-4 PLN/senior/mies. — pomijalny vs 149 PLN przychodu.

---

## 11. Kluczowe wnioski

1. **Break-even od pierwszego seniora** (bez kosztów zespołu)
2. **Marża 57%** (84,50 PLN/senior) przy cenie rynkowej 149 PLN
3. **Główne koszty:** telefonia (56% kosztów zmiennych) + TTS (30%) — LLM to tylko 5%
4. **Skumulowany cash po 12 mies.: ~29 100 PLN** — kapitał na decyzje kadrowe
5. **Przy 85 seniorach** przepływ miesięczny (+7 037 PLN) pokrywa 1 etat (~7 000 PLN)
6. **Modele zachodnie** (Anthropic/OpenAI) eliminują blokadę mentalną klientów przy pomijalnym koszcie
7. **Hermes oferuje więcej niż konkurencja:** quality scoring, trening, board meetings, advanced health check-in, safety check, compliance

---

*Pełny biznesplan: `docs/business/business_plan.md`*
