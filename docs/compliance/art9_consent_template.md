# Wzór zgody na przetwarzanie danych zdrowotnych (Art. 9 RODO)

**Wersja:** 1.0
**Data:** 2026-07-22
**Język:** Polski

---

## Tekst zgody (odczytywany seniorowi)

Szanowny Panie / Szanowna Pani,

Podczas naszych codziennych rozmów będę pytać Pana/Panią o samopoczucie, nastrój, zdrowie, przyjmowanie leków oraz o to, czy czuje się Pan/Pani bezpiecznie w domu.

Te informacje są danymi zdrowotnymi, które zgodnie z prawem wymagają Pana/Pani wyraźnej zgody.

**Proszę o odpowiedź:**

1. **Czy wyraża Pan/Pani zgodę na zbieranie informacji o Pana/Pani samopoczuciu i zdrowiu podczas naszych rozmów?**
   - [ ] Tak / [ ] Nie

2. **Czy wyraża Pan/Pani zgodę na przekazywanie tych informacji wyznaczonym członkom Pana/Pani rodziny w formie raportu?**
   - [ ] Tak / [ ] Nie
   - Jeśli tak, proszę wskazać kogo: ___________________

3. **Czy wyraża Pan/Pani zgodę na zapisywanie treści rozmów (transkrypcji) w celu dokumentowania opieki?**
   - [ ] Tak / [ ] Nie

4. **Czy wyraża Pan/Pani zgodę na wykorzystanie treści rozmów do ulepszania naszego systemu AI?**
   - [ ] Tak / [ ] Nie
   - *(Opcjonalne — odmowa nie wpływa na usługę)*

**Może Pan/Pani wycofać każdą z tych zgód w dowolnym momencie, informując nas o tym podczas rozmowy lub przez rodzinę. Wycofanie zgody nie wpływa na zgodność z prawem przetwarzania dokonanego przed wycofaniem.**

---

## Struktura techniczna (consent.json)

```json
{
  "senior_id": "<id>",
  "status": "granted",
  "scopes": [
    "transcribe",
    "store_transcript",
    "share_with_family",
    "train_on_transcripts",
    "health_data_explicit"
  ],
  "health_consent": true,
  "health_consent_granted_at": "<timestamp>",
  "family_recipients": ["<imię i relacja członka rodziny>"],
  "granted_at": "<timestamp>",
  "language": "pl",
  "method": "verbal",
  "witness": null,
  "transcript": "<ścieżka do transkrypcji pierwszej rozmowy z zgodą>",
  "notes": "Explicit Art. 9 consent obtained during first call"
}
```

---

## Procedura uzyskiwania zgody

1. **Pierwsza rozmowa** — operator odczytuje klauzulę informacyjną (privacy_policy.md, skrócona wersja)
2. **Pytanie o zgodę** — operator zadaje 4 pytania powyżej, notuje odpowiedzi
3. **Zapisanie zgody** — system `ConsentStore` zapisuje `consent.json` z scope `health_data_explicit`
4. **Weryfikacja** — przy każdej kolejnej rozmowie system sprawdza status zgody
5. **Wycofanie** — senior może wycofać zgodę w dowolnym momencie (komenda `consent revoke`)

---

## Implementacja w kodzie

### Nowy scope: `health_data_explicit`

Dodatkowy scope w `ConsentStore` oznaczający explicit Art. 9 consent. Wymagany zanim `health_consent` może być `True`.

### Zmiana w operator.py

```python
# Przed:
health_consent: bool = True  # ❌ domyślnie True

# Po:
health_consent: bool = False  # ✅ domyślnie False, wymaga explicit consent
```

### Walidacja w ManagerAgent

Przed rozpoczęciem rozmowy, manager sprawdza:
1. Czy `consent.status == "granted"`
2. Czy `health_data_explicit` w `consent.scopes` (jeśli operator ma pytać o zdrowie)
3. Jeśli nie — operator nie pyta o zdrowie, tylko o samopoczucie ogólne

---

*Dokument wygenerowany przez Compliance & DPO Officer (AI) — 2026-07-22*
