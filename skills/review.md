---
name: quality-review
description: Review content for accuracy, clarity, and completeness
trigger: When the orchestrator needs quality evaluation of content
---

# Quality Review Skill

## Steps

1. **Read thoroughly** — Understand the content fully
2. **Check accuracy** — Compare claims against research context
3. **Evaluate clarity** — Is it clear to the target audience?
4. **Assess completeness** — Does it cover all required aspects?
5. **Decide** — PASS (score 8+) or REVISE (score <8)

## Review Criteria

| Criterion | Weight | Description |
|-----------|--------|-------------|
| Accuracy | 30% | Facts match research, no hallucinations |
| Clarity | 25% | Easy to understand, well-structured |
| Completeness | 25% | Covers all aspects of the task |
| Polish | 20% | Grammar, formatting, flow |

## Decision Rules

- **PASS**: Score >= 8/10, no critical accuracy issues
- **REVISE**: Score < 8/10 OR any factual errors found
