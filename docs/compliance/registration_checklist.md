# Checklista rejestracji firmy — Hermes AI Wellness Call Center

**Data:** 2026-07-22
**Autor:** Compliance & DPO Officer (AI)
**Status:** Wymaga działania właściciela

---

## Wybór formy prawnej

### Opcja A: Jednoosobowa Działalność Gospodarcza (JDG)
- **Koszt:** 100 PLN (rejestracja w CEIDG)
- **Czas:** 1-2 dni robocze
- **Odpowiedzialność:** Pełna, osobista
- **ZUS:** Składki obowiązkowe
- **Księgowość:** Uproszczona (KPiR)
- **Rekomendacja:** ✅ Najszybsza opcja do startu

### Opcja B: Spółka z o.o.
- **Koszt:** 1500 PLN (KRS) + 250 PLN (notariusz)
- **Czas:** 1-2 tygodnie
- **Odpowiedzialność:** Ograniczona do kapitału (min. 5000 PLN)
- **Wymagane:** Umowa spółki, kapitał zakładowy, zarząd
- **Rekomendacja:** Rozważyć przy skalowaniu

---

## Checklista — JDG (rekomendowana)

### Krok 1: Rejestracja w CEIDG (1-2 dni)
- [ ] Wybrać nazwę firmy
- [ ] Określić kody PKD (główny: 86.90.E — pozostała działalność w zakresie opieki zdrowotnej; dodatkowe: 62.01.Z — programowanie, 70.22.Z — doradztwo biznesowe)
- [ ] Zarejestrować online na ceidg.gov.pl (wymaga Profilu Zaufanego lub e-Dowodu)
- [ ] Otrzymać NIP (nadawany automatycznie)
- [ ] Otrzymać REGON (nadawany automatycznie)

### Krok 2: Konto bankowe firmowe (1 dzień)
- [ ] Otworzyć konto firmowe (wymagane do rozliczeń)
- [ ] Powiązać konto z NIP

### Krok 3: ZUS (do 7 dni od rozpoczęcia działalności)
- [ ] Zgłosić do ubezpieczeń (ZUS ZUA)
- [ ] Lub zgłosić ulgę na start (6 miesięcy bez składek społecznych)

### Krok 4: Urząd Skarbowy
- [ ] Wybrać formę opodatkowania (ryczałt, liniowy, zasady ogólne)
- [ ] Zgłosić metodę rozliczeń (gotówka/maestralna)

### Krok 5: RODO compliance
- [ ] Wyznaczyć data controller (właściciel)
- [ ] Rejestr przetwarzania (Art. 30) — w `docs/compliance/processing_register.md`
- [ ] Privacy policy — gotowe w `docs/compliance/privacy_policy.md`
- [ ] DPIA — w `docs/compliance/dpia.md`
- [ ] Zgody seniorów — system consent gates działa
- [ ] Umowa powierzenia z OpenRouter — do zawarcia

### Krok 6: Polityki wewnętrzne
- [ ] Polityka retencji — gotowa w `docs/compliance/retention_policy.md`
- [ ] Polityka bezpieczeństwa danych
- [ ] Procedura obsługi naruszeń (data breach)
- [ ] Procedura obsługi wniosków osób (data subject requests)

### Krok 7: Infrastruktura IT
- [ ] Szyfrowanie danych w spoczynku
- [ ] Szyfrowanie danych w tranzycie (HTTPS/TLS)
- [ ] Backup danych
- [ ] Kontrola dostępu (autoryzacja, autentykacja)
- [ ] Logi audytu — ✅ działa

---

## Po rejestracji — aktualizacja systemu

Po uzyskaniu NIP/KRS należy zaktualizować:

1. `docs/compliance/privacy_policy.md` — wstawić nazwę firmy, NIP, KRS, adres
2. `docs/compliance/processing_register.md` — wstawić dane administratora
3. `data/company/state.json` — opcjonalnie dodać dane rejestrowe
4. Raporty rodzinne — dodać klauzulę informacyjną z danymi controllera
5. Disclosure skill (operator) — dodać nazwę firmy do skryptu pierwszej rozmowy

---

## Szacowany koszt startowy

| Pozycja | Koszt |
|---------|-------|
| Rejestracja CEIDG | 0 PLN (online) |
| Konto bankowe | 0-50 PLN/mies |
| ZUS (ulga na start) | 0 PLN przez 6 mies |
| ZUS (po 6 mies) | ~1600 PLN/mies |
| Księgowość | 200-400 PLN/mies |
| **Razem (pierwsze 6 mies)** | **~3000 PLN** |

---

*Dokument wygenerowany przez Compliance & DPO Officer (AI) — 2026-07-22*
