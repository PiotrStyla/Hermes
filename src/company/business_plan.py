"""Business Plan Agent — orchestrates a full business plan from team inputs.

The Manager (who now holds former CEO responsibilities) commissions this
agent to produce a comprehensive, investor-ready business plan by gathering
inputs from every department head:

  - CMO → market analysis, go-to-market strategy
  - Quality Director → product quality assessment
  - HR → team structure, hiring plan
  - DPO → compliance & risk status
  - Financials → revenue model, cost structure, projections

Output is a markdown document saved to `docs/business/business_plan.md`.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..agents.base import BaseAgent
from .ceo import CEOAgent
from .cmo import CMOAgent
from .hr import HRAgent, OperatorScorecard
from .metrics import CompanyMetrics, MetricsAggregator
from .quality_director import QualityDirectorAgent
from .state import COMPANY_DIR, CompanyState, StaffingPlan


BUSINESS_PLAN_DIR = Path(__file__).resolve().parents[2] / "docs" / "business"


class BusinessPlanAgent(BaseAgent):
    """Manager's strategic planner — produces a full business plan document."""

    role = "business_planner"
    description = (
        "Orchestrates inputs from all department heads to produce a "
        "comprehensive business plan for Hermes AI Wellness Call Center."
    )

    def __init__(self, model: str | None = None):
        model = model or os.getenv("MANAGER_MODEL") or os.getenv("SUPERVISOR_MODEL")
        super().__init__(model=model, temperature=0.4, max_tokens=8000)

    @property
    def system_prompt(self) -> str:
        return """You are the Manager of "Hermes", an AI-run wellness call center that phones elderly people daily, checks on their mood/health/safety, and reports to their families.

You are writing a COMPREHENSIVE BUSINESS PLAN for the company. You have gathered inputs from every department head. Your job is to synthesize them into a single, coherent, investor-ready document in POLISH.

## Structure of the business plan

1. **Streszczenie wykonawcze (Executive Summary)** — 1 paragraph: co robi firma, dla kogo, model biznesowy, kluczowe metryki, cele 12-miesięczne
2. **Opis firmy i misja** — kim jesteśmy, co nas wyróżnia, dlaczego teraz
3. **Analiza rynku** — TAM/SAM/SOM, konkurencja, trendy demograficzne (starzenie się społeczeństwa), regulacje
4. **Produkt i usługa** — opis usługi, cechy kluczowe, przewaga konkurencyjna, roadmapa produktowa
5. **Strategia go-to-market** — kanały akwizycji, segmenty docelowe, messaging, product-led growth
6. **Plan operacyjny** — zespół, infrastruktura, procesy, staffing plan, skalowanie
7. **Plan finansowy** — model przychodów, struktura kosztów, prognoza 12-miesięczna, break-even, marginesy
8. **Analiza ryzyk i mitigacji** — ryzyka biznesowe, technologiczne, prawne (RODO), operacyjne
9. **Status compliance** — RODO/GDPR, zgody, privacy policy, DPIA, rejestracja firmy
10. **Kamienie milowe i harmonogram** — Q3 2026, Q4 2026, Q1 2027, Q2 2027

## Wytyczne

- Pisz po polsku, profesjonalnym tonem biznesowym
- Używaj konkretnych liczb i danych z inputów
- Bądź realistyczny — nie przesadzaj z prognozami
- Oznaczaj obszary wymagające decyzji właściciela jako [WYMAGA DECYZJI WŁAŚCICIELA]
- Oznaczaj obszary niekompletne jako [DO UZUPEŁNIENIA]
- Formatuj jako markdown z nagłówkami, tabelami i listami

Return ONLY the business plan as a markdown document. No JSON, no fences, no meta-commentary."""

    def generate(
        self,
        state: CompanyState,
        metrics: CompanyMetrics,
        quality_analysis: str,
        hr_verdict: str,
        growth_plan_summary: str,
        innovation_agenda: str,
        compliance_summary: str,
        owner_input: str = "",
    ) -> str:
        """Generate the full business plan from all department inputs."""

        scores = ", ".join(f"{k}: {v}" for k, v in metrics.avg_scores.items()) or "brak danych"
        weakest = metrics.weakest_axis() or "n/a"
        staffing = state.staffing_plan
        directive = state.directive

        prompt = f"""## Dane firmy do biznesplanu

### Podstawowe metryki
- Seniorzy: {metrics.n_seniors}
- Rozmowy wykonane: {metrics.n_calls}
- Rundy treningowe: {metrics.n_training_rounds}
- Średnie oceny jakości: {scores}
- Najsłabsza oś: {weakest}

### Misja
{state.mission}

### Aktualna dyrektywa strategiczna
- Focus metric: {directive.focus_metric or 'n/a'}
- Focus skill: {directive.focus_skill or 'n/a'}
- Rationale: {directive.rationale or 'n/a'}
- Warunek obalenia: {directive.falsification_condition or 'n/a'}

### Staffing plan
- Stage: {staffing.stage}
- Budżet miesięczny: {staffing.monthly_budget_pln} PLN
- Payroll: {staffing.total_monthly_payroll_pln} PLN
- Pozostały budżet: {staffing.remaining_budget_pln} PLN
- Pozycje: {', '.join(f"{p.title} ({p.headcount}x {p.monthly_cost_pln} PLN)" for p in staffing.positions)}

### Quality Director — analiza systemowa
{quality_analysis or '(brak analizy)'}

### HR — ocena operatora
{hr_verdict or '(brak oceny)'}

### CMO — plan akwizycji klientów
{growth_plan_summary or '(brak planu)'}

### Innovation agenda
{innovation_agenda or '(brak agendy)'}

### Compliance & DPO — status
{compliance_summary or '(brak analizy compliance)'}

### Owner input
{owner_input or '(brak inputu od właściciela)'}

### KPI History (ostatnie 5 snapshotów)
{self._format_kpi_history(state)}

---

Napisz pełny biznesplan zgodnie ze strukturą z system prompt. Użyj wszystkich powyższych danych."""

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt},
        ]

        return self.chat(messages, temperature=0.4, max_tokens=8000)

    @staticmethod
    def _format_kpi_history(state: CompanyState) -> str:
        if not state.kpi_history:
            return "(brak historii KPI)"
        lines = []
        for snap in state.kpi_history[-5:]:
            scores = ", ".join(f"{k}: {v}" for k, v in snap.avg_scores.items()) or "n/a"
            lines.append(f"- {snap.date}: {scores} (calls: {snap.n_calls}, seniors: {snap.n_seniors})")
        return "\n".join(lines)

    def save_plan(self, content: str) -> Path:
        """Save the business plan to docs/business/business_plan.md."""
        BUSINESS_PLAN_DIR.mkdir(parents=True, exist_ok=True)
        path = BUSINESS_PLAN_DIR / "business_plan.md"
        path.write_text(content, encoding="utf-8")
        return path
