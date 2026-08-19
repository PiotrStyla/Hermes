# Business Plan: Hermes – AI Wellness Call Center dla Seniorów

## 1. Streszczenie wykonawcze

Hermes to AI-obsługiwane call center wellness, które codziennie telefonuje do osób starszych, sprawdza ich samopoczucie, stan zdrowia i bezpieczeństwo, a następnie raportuje najbliższej rodzinie. Działamy w modelu subskrypcyjnym B2C, gdzie dorosłe dzieci seniorów płacą 149 PLN/mies. za spokój ducha — wiedząc, że rodzic jest codziennie otoczony troską, nawet gdy oni są daleko. Nasz całkowicie zewnętrzny stos technologiczny (ElevenLabs TTS, OpenAI/Anthropic LLM, Plivo telefonia, i żadnych własnych modeli) pozwala na błyskawiczne skalowanie bez kosztów kapitałowych. Po 98 zrealizowanych rozmowach z 2 seniorami osiągamy średnią ocen: warmth 8.8/10, listening 8.2/10, informacja 6.2/10, zwięzłość 8.2/10. Koszt infrastruktury na seniora wynosi ~65 PLN/mies., co daje marżę brutto 56% na każdym subskrybencie. W ciągu 12 miesięcy planujemy pozyskać 85 płacących rodzin, osiągając miesięczny przychód 12 665 PLN przy kosztach infrastruktury 5 695 PLN.

---

## 2. Opis firmy i misja

Hermes jest odpowiedzią na cichy kryzys opieki nad osobami starszymi w Polsce. Jestemy AI-wellness call center, które wykonuje codzienne telefony do seniorów — nie jako bot, ale jako empatyczny, ciepły rozmówca, który naprawdę słucha. Nasza misja: *„Provide warm, attentive daily wellness check-in calls to elderly people, keep their families informed, and continuously improve the quality of care.”*

Co nas wyróżnia:
- **Pełny outsourcing technologiczny** — nie budujemy własnych modeli, TTS ani infrastruktury. Cały stos to ElevenLabs, OpenRouter, Plivo/Twilio. To pozwala nam skupić się na jakości interakcji i kosztach operacyjnych, a nie na inżynierii ML.
- **Analiza jakości w czasie rzeczywistym** — mamy własny system oceniania (warmth, listening, info_quality, brevity), który pozwala na ciągłe doskonalenie agentów AI.
- **Transparentność dla rodzin** — każdy kontakt kończy się raportem zdrowotnym i samopoczuciowym wysyłanym do rodziny seniora.

**Dlaczego teraz:** Polska się starzeje. 7,2 mln osób ma 65+ lat, a 1,4 mln mieszka samotnie. Dorosłe dzieci często mieszkają w dużych miastach lub za granicą. Potrzeba jest ogromna, a rynek dopiero się tworzy.

---

## 3. Analiza rynku

| Segment | Wielkość | Opis |
|---------|----------|------|
| **TAM (Total Addressable Market)** | 7,2 mln seniorów 65+ w Polsce | Każda osoba starsza, która mogłaby skorzystać z codziennego kontaktu wellness |
| **SAM (Serviceable Addressable Market)** | 1,4 mln seniorów 75+ mieszkających samotnie | Segment z największą potrzebą codziennej kontroli; ich dzieci są głównymi decydentami zakupu |
| **SOM (Serviceable Obtainable Market)** | 10 000 rodzin w pierwszym roku | Oparte na dostępności budżetu marketingowego (50 000 PLN/mies. na akwizycję) i współczynniku konwersji z social mediów |

**Konkurencja bezpośrednia (AI teleopieka głosowa):**

| Usługa | Cena (PLN/mies) | Co oferuje |
|--------|----------------|------------|
| **opiekunek.pl — Free** | 0 | SMS o lekach, 2 rozmowy/tydz, raport tygodniowy |
| **opiekunek.pl — Opiekun** | 149 | Codzienne rozmowy (≤15 min), SMS, 2 próby, raport codzienny |
| **opiekunek.pl — Opiekun+** | 299 | Codzienne rozmowy (≤30 min), 3 próby, raport codzienny |
| **eOpiekun.pl** | 149 | Codzienne rozmowy 7 dni/tydz, monitoring leków/wody, raport tygodniowy |

**Zniżki wieloosobowe (opiekunek.pl):** 2 seniorów — 127 PLN/os., 3 — 114 PLN/os., 4 — 104 PLN/os.

**Konkurencja pośrednia (teleopieka z opaską SOS):**

| Usługa | Abonament (PLN/mies) | Sprzęt (jednorazowo) |
|--------|----------------------|---------------------|
| Bezpieczna Rodzina | 69 (pakiet 12-mies) | 299-649 PLN |
| Senior Alert | 32 (+18 za dodatki) | 200-350 PLN |
| PZU Zdrowie | 78 | 500-800 PLN |
| Teleopieka24 | 45-65 | varies |

**Opieka stacjonarna (referencja):** opiekunka z zamieszkaniem 6 000-12 000 PLN/mies., prywatny dom opieki 5 000-15 000 PLN/mies.

**Aplikacje mobilne** (SeniorApp) — rynek opiekunek godzinowych, 15% prowizji od usługi, nie bezpośredni konkurent.

**Urządzenia IoT** (opaski SOS) — 30-80 PLN/mies. abonament + 200-800 PLN sprzęt, brak elementu ludzkiego kontaktu.

**Trendy demograficzne:** Do 2030 roku liczba Polaków 80+ wzrośnie o 40%. Jednocześnie maleje liczba osób w wieku produkcyjnym, co zwiększa popyt na zdalne rozwiązania opiekuńcze.

**Regulacje:** RODO (GDPR) nakłada szczególne wymogi w zakresie danych zdrowotnych (Art. 9) i danych osób starszych. Jesteśmy zgodni z Art. 9 — wymagamy jawnej, dobrowolnej zgody na przetwarzanie danych zdrowotnych, a domyślnie `health_consent` jest False.

---

## 4. Produkt i usługa

Hermes to codzienny, automatyczny telefon wellness do seniora. Rozmowa trwa zazwyczaj 3–5 minut i obejmuje:
1. **Powitanie i sprawdzenie samopoczucia** — „Dzień dobry, jak się Pani dzisiaj czuje?”
2. **Health check-in** — pytania o leki, choroby przewlekłe, ogólny stan zdrowia. **Krytyczne** — to nasza najsłabsza oś (info_quality 6.2) i priorytet strategiczny.
3. **Kontrola bezpieczeństwa** — czy senior jest bezpieczny, czy ma jedzenie, czy nie ma niepokojących objawów.
4. **Zakończenie i raport** — „Dziękuję za rozmowę. Do jutra!”; raport wysyłany do rodziny.

**Kluczowe cechy:**
- **Głos ludzki i ciepły** — dzięki ElevenLabs TTS wybrano głos naturalny, a nie robotyczny.
- **Słuchanie aktywne** — system został zaprojektowany, by zadawać pytania uzupełniające po „Nie wiem” lub niejasnych odpowiedziach.
- **Raporty dla rodzin** — automatycznie generowane po każdej rozmowie, zawierające ocenę samopoczucia, stan zdrowia, alerty.

**Przewaga konkurencyjna:**
- **Koszt** — 149 PLN/mies. (równo z opiekunek.pl i eOpiekun.pl, ale z bogatszą ofertą).
- **Częstotliwość** — codziennie vs raz w tygodniu u tradycyjnych call center.
- **Skalowalność** — zero infrastruktury własnej; każda nowa rodzina to tylko dodatkowy koszt API.
- **Więcej funkcji niż konkurencja** — quality scoring (4 osie), self-play trening, board meetings, advanced health check-in (leki, choroby, ból, sen, apetyt), safety check (czujniki dymu, upadki, kontakty), compliance/RODO.

**Roadmapa produktowa:**
- **Q3 2026:** Naprawa health-checkin (hard-coded mandatory steps w prompt layer), testy A/B 3 wariantów messagingu.
- **Q4 2026:** Wprowadzenie Context-Aware Response Quality Engine (info_quality ≥ 7.5), Real-Time Unit Economics Dashboard.
- **Q1 2027:** Uruchomienie programu referencyjnego, publikacja postów na forach senioralnych i LinkedIn.
- **Q2 2027:** Pilotaż Embedded Voice-Agent API dla SMB (10 integracji).

---

## 5. Strategia go-to-market

**Segmenty docelowe:**
1. Dorosłe dzieci seniorów (30–55 lat) mieszkające w innym mieście lub za granicą.
2. Samotni seniorzy 75+ mieszkający samodzielnie (pośrednio — przez dzieci).

**Kanały akwizycji:**
| Kanał | Koszt mies. | Spodziewany leadów/mies. | Koszt za lead |
|-------|------------|--------------------------|----------------|
| Posty na forach senioralnych | 0 PLN (organic) | 50 | 0 PLN |
| LinkedIn (content marketing) | 0 PLN (organic) | 30 | 0 PLN |
| X/Twitter (insighty wellness) | 0 PLN (organic) | 20 | 0 PLN |
| Referral prompt w rozmowie | 0 PLN (wbudowane) | 15 | 0 PLN |
| Automatyczne raporty dla rodzin | 0 PLN (wbudowane) | 25 | 0 PLN |

**Strategia kosztowa:** Cały marketing oparty na content marketingu i referencjach — zero płatnych reklam w pierwszych 6 miesiącach.

**Messaging:**
> *„Codzienny, ciepły telefon do Twojego rodzica i jasny raport dla Ciebie — spokój ducha, gdy nie możesz być obok.”*

**Product-led growth:**
- Automatyczne raporty dla rodzin są wirusowe — rodzina wysyła je dalej do rodzeństwa.
- Referral prompt w skrypcie zamykającym rozmowę: operator prosi zadowolone rodziny o polecenie.

**[WYMAGA DECYZJI WŁAŚCICIELA]** Czy uruchomić płatne reklamy na Facebook/Instagram przed Q2 2027? Koszt: 10 000 PLN/mies. za test A/B.

---

## 6. Plan operacyjny

**Zespół (stage: standard, budżet: 192 000 PLN/mies.):**

| Rola | Liczba | Wynagrodzenie (PLN/mies.) |
|------|--------|--------------------------|
| Manager | 1 | 18 000 |
| Supervisor | 1 | 16 000 |
| Operator | 2 | 24 000 (12 000 każdy) |
| Quality Director | 1 | 22 000 |
| Training Engineer | 1 | 17 000 |
| MLOps/SRE Engineer | 1 | 15 000 |
| CMO | 1 | 20 000 |
| Customer Success Specialist | 1 | 10 000 |
| Compliance & DPO Officer | 1 | 13 000 |
| Cybersecurity Officer | 1 | 9 000 |
| HR Officer | 1 | 16 000 |
| Księgowy | 1 | 7 000 |
| **Razem** | **13** | **187 000** |
| *Budżet rezerwowy* | | *5 000* |

**Infrastruktura (w pełni zewnętrzna — zero własnych serwerów i modeli):**

| Komponent | Provider | Cena | Notatki |
|-----------|----------|------|--------|
| **TTS** | ElevenLabs API (Flash/Turbo) | $0.05/1K znaków | Naturalny głos po polsku; Multilingual v2/v3: $0.10/1K znaków |
| **STT** | ElevenLabs Scribe | $0.22/godz. | Transkrypcja rozmowy do analizy jakości |
| **LLM (Operator)** | Claude Haiku 4.5 (Anthropic) | $1.00/1M in, $5.00/1M out | Zachodni provider, DPA dostępne, brak blokady mentalnej klientów |
| **LLM (Supervisor/inni)** | GPT-4o-mini (OpenAI) | $0.15/1M in, $0.60/1M out | Najtańszy zachodni model, wystarczający do oceny jakości |
| **Telefonia** | Plivo | $0.027/min (stacjonarne), $0.058/min (komórkowe EEA) | Numer telefonu ~$1/mies. |
| **Hosting** | Railway/Render VPS | ~$15/mies. | Python app + PostgreSQL |
| **Email** | Mailgun/SendGrid | ~$5/mies. | Wysyłka raportów rodzinnych |
| **Płatności** | Stripe | 2.5% + 1 PLN/transakcja | Subskrypcje B2C |

**Porównanie modeli LLM (zachodnie vs chińskie):**

| Model | Input $/1M | Output $/1M | Koszt/senior/mies | Trust factor | DPA/RODO |
|-------|-----------|------------|-----------------|--------------|----------|
| **GPT-4o-mini** (OpenAI) | $0.15 | $0.60 | ~0.43 PLN | Wysoki | Tak |
| **Claude Haiku 4.5** (Anthropic) | $1.00 | $5.00 | ~3.30 PLN | Wysoki | Tak |
| **Claude Sonnet 5** (Anthropic) | $2.00 | $10.00 | ~6.60 PLN | Najwyższy | Tak |
| **GPT-4o** (OpenAI) | $2.50 | $10.00 | ~7.20 PLN | Wysoki | Tak |
| ~~z-ai/glm-5.2~~ (chiński) | ~$0.07 | ~$0.28 | ~0.25 PLN | Niski (blokada klientów) | Niejasne |

**Rekomendacja: Claude Haiku 4.5 dla Operatora + GPT-4o-mini dla Supervisora/agentów pomocniczych.**
- Koszt LLM łącznie: ~3-4 PLN/senior/mies. (pomijalnie mało vs 149 PLN przychodu)
- Zachodnie, zaufane providery z DPA — brak blokady mentalnej klientów
- Anthropic znany z safety/compliance — istotne dla danych zdrowotnych seniorów
- Nawet najdroższy zachodni model (GPT-4o: 7.20 PLN) to 5% ceny — różnica vs chiński (0.25 PLN) jest pomijalna przy 149 PLN przychodu

**Procesy kluczowe:**
1. **Rejestracja seniora:** Formularz online dla rodziny → zgoda Art. 9 → aktywacja.
2. **Codzienna rozmowa:** Automatyczny trigger o ustalonej porze → LLM generuje rozmowę → ElevenLabs TTS → Plivo dzwoni → Analiza jakości → Raport.
3. **Eskalacja:** Jeśli senior zgłasza problem zdrowotny lub nie odbiera → alert do rodziny i opcjonalnie do służb.

**Staffing — do decyzji właściciela (pominięto w kosztach powyżej):**
- System działa w pełni autonomicznie (AI agenci wykonują wszystkie funkcje)
- Koszty zespołu będą dodane po decyzji właściciela o strukturze zatrudnienia
- Przy 85 seniorach przepływ gotówki (+7 037 PLN/mies.) pokrywa 1 etat (~7 000 PLN)

---

## 7. Plan finansowy (koszty infrastruktury, bez kosztów zespołu)

**Model przychodów:**
- Subskrypcja miesięczna: **149 PLN/seniora** (cena rynkowa — równe z opiekunek.pl i eOpiekun.pl)
- Rabat za polecenie: 10% dla polecającego i nowego klienta przez 3 miesiące
- Brak dodatkowych opłat (za konfigurację, za sprzęt)

**Założenia techniczne na 1 seniora/miesiąc:**
- 30 rozmów/mies., średnio 7 min/rozmowę (z hard block safety check)
- TTS: ~3 150 znaków/rozmowę × 30 = 94 500 znaków (Flash API)
- STT: ~3,5 min/rozmowę × 30 = 105 min transkrypcji
- Telefonia: 210 min/mies. (50% stacjonarne, 50% komórkowe EEA)
- LLM: ~10 000 input + 3 500 output tokenów/rozmowę (Operator + Supervisor + Manager)

**Koszty zmienne na 1 seniora/miesiąc:**

| Komponent | Koszt (PLN) | Wyliczenie |
|-----------|-------------|------------|
| ElevenLabs TTS (Flash API) | 19,00 | 94 500 znaków × $0.05/1K = $4.73 |
| ElevenLabs STT (Scribe) | 1,50 | 105 min × $0.22/godz. = $0.39 |
| Plivo telefonia (średnia) | 36,00 | 210 min × $0.043/min = $9.03 |
| LLM (Claude Haiku 4.5 + GPT-4o-mini) | 3,30 | ~300K in + 105K out tokenów |
| Stripe (płatności) | 4,75 | 149 × 2.5% + 1 PLN |
| **Razem koszty zmienne** | **~64,50 PLN** | |

**Marża na seniorze: 149 - 64,50 = 84,50 PLN (57%)**

**Koszty stałe (miesięczne):**

| Komponent | Koszt (PLN) |
|-----------|-------------|
| Hosting (Railway/Render VPS) | 60 |
| Email (Mailgun/SendGrid) | 20 |
| Plivo numer telefonu | 4 |
| LLM — board meetings + trening (Haiku 4.5) | 25 |
| Monitoring/logging | 10 |
| Domena | 1 |
| **Razem koszty stałe** | **~120 PLN/mies.** |

*Notatka: Koszty stałe rosną minimalnie przy skali (>50 seniorów: +1 numer telefonu na każde 20 seniorów, hosting upgrade przy >100).*

**Koszty jednorazowe:**
- Rejestracja firmy (JDG): 0 PLN (CEIDG)
- DPA z OpenAI/Anthropic: 0 PLN (standardowe umowy)
- Compliance setup (privacy policy, DPIA): 0 PLN (wygenerowane wewnętrznie)

**Przepływ gotówki — prognoza 12-miesięczna (wyłącznie infrastruktura):**

| Miesiąc | Seniorzy | Przychód | Koszty zmienne | Koszty stałe | **Przepływ netto** | **Skumulowany** |
|---------|----------|----------|----------------|--------------|---------------------|-----------------|
| M1 (wrz 2026) | 2 | 298 | 129 | 120 | **+49** | 49 |
| M2 (paź) | 3 | 447 | 194 | 120 | **+133** | 182 |
| M3 (lis) | 5 | 745 | 323 | 120 | **+302** | 484 |
| M4 (gru) | 8 | 1 192 | 516 | 125 | **+551** | 1 035 |
| M5 (sty 2027) | 12 | 1 788 | 774 | 125 | **+889** | 1 924 |
| M6 (lut) | 18 | 2 682 | 1 161 | 130 | **+1 391** | 3 315 |
| M7 (mar) | 25 | 3 725 | 1 613 | 130 | **+1 982** | 5 297 |
| M8 (kwi) | 35 | 5 215 | 2 258 | 135 | **+2 822** | 8 119 |
| M9 (maj) | 45 | 6 705 | 2 903 | 135 | **+3 667** | 11 786 |
| M10 (cze) | 55 | 8 195 | 3 548 | 140 | **+4 507** | 16 293 |
| M11 (lip) | 70 | 10 430 | 4 515 | 140 | **+5 775** | 22 068 |
| M12 (sie) | 85 | 12 665 | 5 483 | 145 | **+7 037** | 29 105 |

**Wyniki po 12 miesiącach:**
- Przychód miesięczny: 12 665 PLN
- Koszty miesięczne: 5 628 PLN
- Przepływ netto miesięczny: +7 037 PLN
- Przepływ skumulowany: +29 105 PLN
- **Break-even infrastruktury: od M1** (pozytywny przepływ od pierwszego miesiąca)

**Wrażliwość marży:**

| Scenariusz | Cena | Koszt/senior | Marża/senior | Marża % |
|-----------|------|-------------|-------------|---------|
| Bazowy (149 PLN, Flash TTS, avg telefony) | 149 | 64,50 | 84,50 | 57% |
| Premium (149 PLN, Multilingual TTS) | 149 | 83,50 | 65,50 | 44% |
| Tylko komórkowe (149 PLN, mobile EEA) | 149 | 72,50 | 76,50 | 51% |
| Promocja -10% (134 PLN) | 134 | 64,50 | 69,50 | 52% |
| Opiekun+ konkurencja (299 PLN) | 299 | 64,50 | 234,50 | 78% |

**Wnioski finansowe:**
1. Model jest zyskowny od pierwszego seniora (bez kosztów zespołu)
2. Marża 57% na każdym seniorze przy cenie rynkowej 149 PLN
3. Główne koszty to telefonia (56% kosztów zmiennych) i TTS (30%)
4. LLM koszt jest pomijalny (5% kosztów zmiennych) — można używać najwyższej jakości modeli zachodnich bez istotnego wpływu na marżę
5. Skumulowany przepływ gotówki po 12 mies.: ~29 000 PLN (kapitał na decyzje kadrowe)
6. Przy 85 seniorach miesięczny przepływ (+7 037 PLN) pokrywa 1 etat przy wynagrodzeniu ~7 000 PLN

---

## 8. Analiza ryzyk i mitigacji

| Ryzyko | Kategoria | Prawdopodobieństwo | Wpływ | Mitigacja |
|--------|-----------|-------------------|-------|-----------|
| **R1: Przetwarzanie danych zdrowotnych bez explicit Art. 9 consent** | Prawne (RODO) | Niskie (już zmienione na `health_consent` default False) | Krytyczne (kara do 20M EUR) | Wymagamy jawnej zgody seniora; dokumentacja w `consent.json`; wzór zgody gotowy |
| **R2: Brak zarejestrowanego data controllera** | Prawne (RODO) | Wysokie (firma niezarejestrowana) | Krytyczne | **WYMAGA WŁAŚCICIELA:** Rejestracja JDG w CEIDG |
| **R3: Brak privacy policy / klauzuli RODO** | Prawne (RODO) | Średnie | Wysokie | Privacy policy (PL) wygenerowana; wymaga uzupełnienia NIP/KRS po rejestracji |
| **R4: Brak umowy powierzenia z OpenRouter** | Prawne (RODO) | Wysokie | Wysokie | **WYMAGA WŁAŚCICIELA:** DPA z OpenRouter; weryfikacja transferu poza EOG (SCCs) |
| **R5: Brak polityki retencji** | Prawne (RODO) | Niskie | Średnie | Polityka zdefiniowana: transkrypcje 90d, notatki 1r, raporty 2r |
| **R7: Udostępnianie raportów rodzinom bez zgody seniora** | Prawne (RODO) | Średnie | Wysokie | Wymagamy explicit consent seniora na sharing z konkretnymi osobami |
| **R8: Brak DPIA** | Prawne (RODO) | Niskie (już przeprowadzone) | Wysokie | DPIA wykonane; warunkowa akceptacja po remediacji |
| **R10: Brak rejestru przetwarzania** | Prawne (RODO) | Średnie | Średnie | Rejestr do utworzenia po rejestracji firmy |
| **Info_quality spadek** | Biznesowe | Wysokie (obserwowany spadek) | Wysokie | Przyjęta dyrektywa strategiczna: health-checkin hard-coded jako mandatory step |
| **Zależność od zewnętrznych API (ElevenLabs, OpenRouter)** | Technologiczne | Średnie | Średnie | Brak lock-in; łatwa migracja do alternatyw; budowa własnych promptów |
| **Niska adopcja** | Biznesowe | Średnie | Wysokie | Marketing organiczny; testy A/B; program referencyjny |

**[WYMAGA DECYZJI WŁAŚCICIELA]** Kto będzie pełnił funkcję Data Controllera po rejestracji firmy? Czy właściciel, czy osoba zewnętrzna (DPO)?

---

## 9. Status compliance

| Obszar | Status | Data realizacji |
|--------|--------|----------------|
| **Rejestracja firmy (JDG lub sp. z o.o.)** | ✗ **WYMAGA WŁAŚCICIELA** | CEIDG, Profil Zaufany |
| **Zgody seniorów (Art. 9 RODO)** | ✓ Zgodne | Dla jadwiga-001 i stefan-001 pełne zgody (transcribe, store, share, health_data, train). `health_consent` default False |
| **Privacy policy (PL)** | ✓ Wygenerowana | Wymaga uzupełnienia NIP/KRS po rejestracji |
| **Retention policy** | ✓ Zdefiniowana | Transkrypcje 90d, notatki 1r, raporty 2r, audyt 3r |
| **DPIA** | ✓ Przeprowadzone | Warunkowa akceptacja po remediacji (health_consent, rejestracja, DPA) |
| **DPA z OpenRouter** | ✗ **WYMAGA WŁAŚCICIELA** | Konieczne przed przetwarzaniem danych na produkcji |
| **Rejestr przetwarzania (Art. 30)** | ✗ Do utworzenia | Po rejestracji firmy |

**Otwarte pozycje (priorytetowe):**
1. **[WYMAGA WŁAŚCICIELA]** Rejestracja firmy (JDG w CEIDG).
2. **[WYMAGA WŁAŚCICIELA]** DPA z OpenRouter (Art. 28 RODO).
3. **[WYMAGA WŁAŚCICIELA]** Weryfikacja transferu danych poza EOG (SCCs).

---

## 10. Kamienie milowe i harmonogram

| Okres | Działanie | Kluczowe wskaźniki | Odpowiedzialny |
|-------|-----------|-------------------|----------------|
| **Q3 2026 (D+0 – D+45)** | **1. Naprawa health-checkin** — hard-code mandatory step w prompt layer, testy A/B | Info_quality ≥ 7.5; health-checkin completion > 80% | Manager, Training Engineer |
| | **2. Rejestracja firmy i DPA** | Firma zarejestrowana; DPA z OpenRouter podpisane | **WŁAŚCICIEL** |
| | **3. Uruchomienie content marketingu** — 5 postów na fora, 3 posty X, 2 LinkedIn | 50 leadów/mies. | CMO |
| | **4. Rozpoczęcie pilotażu z 5 seniorami** | 5 aktywnych subskrypcji | Customer Success Specialist |
| **Q4 2026 (D+45 – D+90)** | **1. Context-Aware Response Quality Engine** — live | Info_quality ≥ 7.5 (potwierdzone) | Manager, MLOps |
| | **2. Real-Time Unit Economics Dashboard** — live | Koszt na rozmowę widoczny; marża ≥ 30% | Manager, MLOps |
| | **3. Program referencyjny** — skrypt zamykający rozmowę gotowy | 15 leadów referencyjnych/mies. | CMO, Operatorzy |
| | **4. Skalowanie do 20 seniorów** | 20 subskrypcji | Supervisor |
| **Q1 2027 (D+90 – D+180)** | **1. Embedded Voice-Agent API dla SMB** — projekt rozpoczęty | 5 pilotów zewnętrznych | Manager |
| | **2. Marketing organiczny — faza 2** — 3 posty na LinkedIn, 5 na fora | 100 leadów/mies. | CMO |
| | **3. Skalowanie do 60 seniorów** | 60 subskrypcji | Supervisor |
| **Q2 2027 (D+180 – D+365)** | **1. Embedded API — 10 integracji** | 10 pilotów z dodatnią marżą | Manager, MLOps |
| | **2. Skalowanie do 120 seniorów** | 120 subskrypcji | Supervisor |
| | **3. Decyzja o płatnych reklamach** | Jeśli koszt leada organicznego > 50 PLN | **WŁAŚCICIEL**, CMO |

**[WYMAGA DECYZJI WŁAŚCICIELA]** Czy rozpocząć skaling do 120 seniorów, czy utrzymać niski poziom i skupić się na jakości? Rekomendacja: osiągnąć 50 seniorów w Q1 2027, potem testować skalę.

**[DO UZUPEŁNIENIA]** Dokładny budżet na marketing organiczny (czas CMO, narzędzia do social media). Szacowany czas CMO: 30% etatu przy content marketingu.

---

## Podsumowanie dla właściciela

Hermes udowadnia, że codzienny, ciepły kontakt wellness dla seniorów jest możliwy w modelu w pełni zewnętrznym, przy zerowych kosztach kapitałowych. Model biznesowy jest zyskowny od pierwszego seniora — marża 57% przy cenie rynkowej 149 PLN.

**Kluczowe liczby:**
- Koszt infrastruktury: ~64,50 PLN/senior/mies.
- Przychód: 149 PLN/senior/mies.
- Marża: 84,50 PLN/senior/mies. (57%)
- Break-even infrastruktury: od M1 (pozytywny przepływ od pierwszego seniora)
- Skumulowany przepływ po 12 mies.: ~29 100 PLN (przy 85 seniorach)

**Kluczowe wyzwania:**
1. **Compliance** — rejestracja firmy i DPA z OpenAI/Anthropic to absolutne must-have przed skalowaniem.
2. **Jakość informacji** — health-checkin musi być poprawiony natychmiast (Dyrektywa Strategiczna z warunkiem obalenia: 14 dni).
3. **Modele LLM** — rekomendacja: Claude Haiku 4.5 (Operator) + GPT-4o-mini (Supervisor). Koszt pomijalny (~3,30 PLN/senior), brak blokady mentalnej klientów, DPA dostępne.
4. **Skala vs jakość** — utrzymać niską liczbę seniorów w Q3 (5–10), skupić się na poprawie info_quality, dopiero potem skalować.
5. **Zespół** — decyzja o strukturze zatrudnienia odłożona. Przy 85 seniorach przepływ pokrywa 1 etat.

Decyzje właściciela wymagane:
- [ ] Rejestracja firmy (JDG czy sp. z o.o.?)
- [ ] Kto data controllerem?
- [ ] Zatwierdzenie modeli: Claude Haiku 4.5 + GPT-4o-mini?
- [ ] Struktura zatrudnienia (po analizie przepływu gotówki)
- [ ] Czy uruchomić płatne reklamy w Q2 2027?

Gotowy do działania.