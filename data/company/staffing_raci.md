# Staffing RACI (Hermes)

## Zakres
Model ról operacyjnych dla autonomicznego działania firmy w trybie `light`, `standard`, `scale`.

## Legenda
- R = Responsible (wykonuje)
- A = Accountable (odpowiada końcowo)
- C = Consulted (konsultowany)
- I = Informed (informowany)

## Role
- CEO
- Compliance & DPO Officer
- Quality Director
- HR Officer
- CMO
- Manager
- Supervisor
- Operator
- Training Engineer
- MLOps/SRE Engineer
- Cybersecurity Officer
- Księgowy
- Customer Success Specialist

## Macierz RACI
| Proces | CEO | DPO | QD | HR | CMO | Manager | Supervisor | Operator | Training | MLOps/SRE | Cyber | Księgowy | CS |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Strategia i priorytety kwartalne | A | C | C | C | C | I | I | I | I | I | I | I | I |
| Jakość rozmów i standardy | I | C | A | C | I | R | R | R | C | I | I | I | C |
| Daily operations i harmonogramy | I | I | C | I | I | A | R | R | I | C | I | I | C |
| Trening modelu i poprawa skilli | I | C | C | I | I | C | C | I | A/R | R | I | I | I |
| Utrzymanie produkcji i niezawodność | I | I | I | I | I | C | I | I | C | A/R | C | I | I |
| Bezpieczeństwo i response na incydenty | I | C | I | I | I | I | I | I | I | C | A/R | I | I |
| RODO/GDPR, zgody, retencja, audyt | I | A/R | C | I | I | C | I | I | I | I | C | C | I |
| Budżet, płynność i kontrola kosztów | A | I | I | I | I | C | I | I | I | I | I | R | I |
| Rozliczenia i payroll | I | I | I | C | I | I | I | I | I | I | I | A/R | I |
| Wzrost i pozyskiwanie klientów | A | I | C | I | R | C | I | I | I | I | I | I | C |
| Obsługa rodzin i eskalacje | I | C | C | I | I | A | C | R | I | I | I | I | R |

## Reguły eskalacji
1. Incydent bezpieczeństwa danych: Cybersecurity Officer (A/R), informacja do DPO i CEO <= 1h.
2. Incydent zgodności: DPO (A/R), konsultacja z Księgowym i Managerem.
3. Spadek jakości KPI < 7.0 przez 2 cykle: Quality Director + Training Engineer plan naprawczy do 48h.
4. Przekroczenie budżetu miesięcznego: Księgowy uruchamia plan cięć, decyzja końcowa CEO.
