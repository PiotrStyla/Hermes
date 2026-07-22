"""Company module — the autonomous AI org chart (executive layer).

Adds the management roles on top of the existing Operator/Supervisor/Manager/
Trainer workforce: a CEO that sets strategy, a Quality Director that finds
systemic quality patterns, HR that reviews operator performance, and a CMO that
plans client acquisition — all governing the company via a persistent
CompanyState.
"""

from .business_plan import BusinessPlanAgent
from .ceo import CEOAgent
from .cmo import CMOAgent
from .hr import HRAgent, OperatorScorecard
from .metrics import CompanyMetrics, MetricsAggregator
from .quality_director import QualityDirectorAgent
from .runner import BoardMeetingResult, CompanyRunner
from .state import (
    CompanyState,
    Decision,
    Directive,
    GrowthPlan,
    KPI_AXES,
    KpiSnapshot,
)

__all__ = [
    "BusinessPlanAgent",
    "CEOAgent",
    "CMOAgent",
    "QualityDirectorAgent",
    "HRAgent",
    "OperatorScorecard",
    "MetricsAggregator",
    "CompanyMetrics",
    "CompanyRunner",
    "BoardMeetingResult",
    "CompanyState",
    "Directive",
    "GrowthPlan",
    "KpiSnapshot",
    "Decision",
    "KPI_AXES",
]
