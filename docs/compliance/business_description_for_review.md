# Hermes — Opis działalności do przeglądu compliance

## Misja
Dziennie wykonywać ciepłe, uważne telefony wellness check-in do osób starszych, informować ich rodziny o stanie zdrowia i samopoczucia, oraz stale poprawiać jakość opieki.

## Model działalności
1. **Automatyczne telefony AI do seniorów** — operator AI dzwoni codziennie do seniorów, przeprowadza rozmowę wellness check-in (nastrój, zdrowie, bezpieczeństwo)
2. **Raporty dla rodzin** — po każdej rozmowie generowany jest raport dla rodziny seniora
3. **Self-play trening** — operator AI trenuje rozmowy na symulowanych seniorach, aktualizuje skille na podstawie ocen supervisor AI
4. **Akwizycja klientów** — product-led referrals (raporty rodzinne z promptem polecającym), gotowe posty na fora/X/LinkedIn (do ręcznego wklejenia)

## Dane przetwarzane
- **Dane osobowe seniorów:** imię, wiek, język, profil zdrowotny (choroby, leki), notatki z rozmów
- **Dane zdrowotne (Art. 9):** samopoczucie, nastrój, ból, przyjmowanie leków, wizyty u lekarza, bezpieczeństwo w domu
- **Transkrypcje rozmów** — pełne zapisy rozmów z seniorami
- **Dane rodzin** — kontakt do rodziny, imiona, relacja z seniorem
- **Dane treningowe** — symulowane rozmowy (self-play), oceny jakości, aktualizacje skilli

## Infrastruktura
- LLM: OpenRouter (openai/gpt-4o-mini) — dane przesyłane do zewnętrznego API
- Brak własnego serwera — działa na komputerze właściciela
- Brak rejestracji firmy — brak NIP, KRS, nazwy prawnej
- Brak privacy policy, brak polityki retencji (w dokumencie)
- Zgody RODO: consent gates w kodzie (transcribe, store_transcript, share_with_family, train_on_transcripts)
- Audit log: wszystkie akcje logowane
- PII redaction: funkcja redact_pii() dostępna
- RetentionPolicy: klasa istnieje w kodzie, brak skonfigurowanej polityki

## Seniorzy
- 2 seniorzy (jadwiga-001, stefan-001)
- Zgody: jadwiga-001 (pełne, pl), stefan-001 (częściowe, en, brak train_on_transcripts)
- health_consent domyślnie True w kodzie operatora

## Ryzyka do oceny
1. Przetwarzanie danych zdrowotnych bez explicit Art. 9 consent
2. Brak zarejestrowanego data controllera
3. Dane przesyłane do zewnętrznego API (OpenRouter/OpenAI)
4. Brak privacy policy dostarczanej seniorom
5. Brak polityki retencji
6. Trening AI na danych z rozmów (purpose limitation)
7. Udostępnianie raportów rodzinom (family sharing bez proxy consent)
8. Akwizycja przez social media — ryzyko ujawnienia danych
9. Brak DPIA (Data Protection Impact Assessment)
10. Brak umowy powierzenia z OpenRouter (processor agreement)
