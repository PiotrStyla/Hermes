# Polityka retencji danych — Hermes AI Wellness Call Center

**Wersja:** 1.0
**Data:** 2026-07-22
**Autor:** Compliance & DPO Officer (AI)
**Podstawa prawna:** Art. 5(1)(e) RODO — Storage limitation

---

## 1. Zasada ogólna

Dane osobowe są przechowywane nie dłużej niż jest to niezbędne do celów, dla których są przetwarzane. Po upływie okresu retencji dane są automatycznie usuwane lub anonimizowane.

## 2. Harmonogram retencji

| Kategoria danych | Okres retencji | Podstawa | Akcja po upływie |
|------------------|---------------|----------|------------------|
| Transkrypcje rozmów | 90 dni od daty rozmowy | Dokumentowanie opieki | Automatyczne usunięcie |
| Raporty rodzinne | 2 lata od wygenerowania | Dokumentacja opieki | Automatyczne usunięcie |
| Notatki zdrowotne seniora | 1 rok od ostatniej aktualizacji | Ciągłość opieki | Anonimizacja |
| Profil seniora (dane identyfikacyjne) | Do wycofania zgody | Świadczenie usługi | Usunięcie (right to erasure) |
| Zgody (consent records) | Do wycofania zgody + 3 lata | Dowód zgody | Usunięcie |
| Logi audytu | 3 lata od zdarzenia | Accountability (Art. 5(2)) | Automatyczne usunięcie |
| Dane treningowe (self-play) | Bezterminowo (dane syntetyczne) | Brak danych osobowych | N/A — dane sztuczne |
| Raporty board meetings | 3 lata | Dokumentacja zarządcza | Automatyczne usunięcie |
| Skill updates (pliki .md) | Bezterminowo | Brak danych osobowych | N/A — metadane techniczne |

## 3. Implementacja techniczna

### Automatyczne usuwanie

System `RetentionPolicy` w kodzie (`src/compliance/retention.py`) obsługuje:

1. **Daily purge job** — uruchamiany codziennie, sprawdza wszystkie pliki seniorów
2. **Dry-run mode** — możliwość podglądu plików do usunięcia bez faktycznego usuwania
3. **Audit log** — każde usunięcie jest logowane w `AuditLog`

### Komendy CLI

```bash
# Podgląd plików do usunięcia (bez usuwania)
python -m src purge --dry-run

# Usuwanie przeterminowanych plików (wszyscy seniorzy)
python -m src purge

# Usuwanie dla konkretnego seniora
python -m src purge --senior-id jadwiga-001
```

### Right to erasure (art. 17)

```bash
# Całkowite usunięcie wszystkich danych seniora
python -m src forget <senior_id> --yes
```

## 4. Wyjątki

- **Obowiązek prawny** — jeśli prawo wymaga dłuższego przechowywania (np. dokumentacja medyczna), stosuje się dłuższy okres
- **Postępowania sądowe** — dane objęte postępowaniem są przechowywane do zakończenia postępowania
- **Zgoda seniora** — senior może wyrazić zgodę na dłuższe przechowywanie (musi być udokumentowana)

## 5. Anonimizacja vs usunięcie

- **Notatki zdrowotne** — po upływie 1 roku dane są anonimizowane (usunięcie identyfikatorów, zachowanie wzorców zdrowotnych dla analizy)
- **Transkrypcje** — całkowite usunięcie (brak możliwości anonimizacji treści rozmowy)
- **Raporty** — całkowite usunięcie
- **Logi audytu** — automatyczne usunięcie po 3 latach

## 6. Weryfikacja

- Miesięczny raport retencji: liczba plików usuniętych, liczba plików przeterminowanych
- Audyt zgodności: kwartalny przegląd polityki retencji
- Logi purge dostępne w audit log

---

*Dokument wygenerowany przez Compliance & DPO Officer (AI) — 2026-07-22*
