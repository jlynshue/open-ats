"""Minimal scoring engine for Sprint 5 (keyword-only).

PRD §FR-7 + §8 specify a multi-category aggregator with configurable
weights per role level. Sprint 8 lands that. For Sprint 5, the engine
accepts the keyword analyzer's result and produces a :class:`Score`
with one :class:`CategoryScore` (keyword), a complete formula audit,
and a rating.

The shape is forward-compatible: when Sprint 6 introduces the
quantification analyzer, the engine accepts a list of analyzer
results and aggregates them via the same formula audit pattern.
"""

from __future__ import annotations

from open_ats.models import (
    AnalyzerResult,
    CategoryScore,
    FormulaAuditEntry,
    Rating,
    Score,
    ScoringConfig,
)


def derive_rating(overall: float) -> Rating:
    """Map a 0–100 score to a Rating per PRD §8."""
    if overall >= 80.0:
        return Rating.EXCELLENT
    if overall >= 70.0:
        return Rating.GOOD
    if overall >= 60.0:
        return Rating.FAIR
    return Rating.POOR


class ScoringEngine:
    """Aggregates analyzer results into a :class:`Score`.

    Sprint 5 supports a single category (keyword); Sprint 8 extends
    this to the full PRD §8 weighted-sum.
    """

    def score(
        self,
        analyzer_results: list[AnalyzerResult],
        config: ScoringConfig,
    ) -> Score:
        if not analyzer_results:
            raise ValueError(
                "ScoringEngine.score requires at least one analyzer result"
            )

        # Sprint 5: only the keyword analyzer's result is fed in. Build a
        # single CategoryScore at weight 1.0 for now; Sprint 8 reads
        # config.weights for proper aggregation.
        categories: list[CategoryScore] = []
        formula_audit: list[FormulaAuditEntry] = []
        overall = 0.0

        for result in analyzer_results:
            weight = config.weights.get(result.analyzer, 1.0)
            contribution = weight * result.score
            categories.append(
                CategoryScore(
                    name=result.analyzer,
                    score=result.score,
                    weight=weight,
                    contribution=round(contribution, 2),
                    sub_scores=dict(result.sub_scores),
                )
            )
            for sub_name, sub_value in sorted(result.sub_scores.items()):
                formula_audit.append(
                    FormulaAuditEntry(
                        step=f"{result.analyzer}.{sub_name}",
                        formula=f"sub_score = {sub_value}",
                        inputs={sub_name: sub_value},
                        output=sub_value,
                    )
                )
            formula_audit.append(
                FormulaAuditEntry(
                    step=f"{result.analyzer}.contribution",
                    formula=f"{weight} * {result.score}",
                    inputs={"weight": weight, "score": result.score},
                    output=round(contribution, 2),
                )
            )
            overall += contribution

        formula_audit.append(
            FormulaAuditEntry(
                step="overall",
                formula="sum of category contributions",
                inputs={c.name: c.contribution for c in categories},
                output=round(overall, 2),
            )
        )

        overall_clamped = max(0.0, min(100.0, overall))
        return Score(
            overall=round(overall_clamped, 2),
            rating=derive_rating(overall_clamped),
            categories=categories,
            formula_audit=formula_audit,
            recommendations=[],  # Sprint 6+ analyzers populate this.
        )


# Module-level singleton convenience.
default_scoring_engine = ScoringEngine()


def keyword_only_config() -> ScoringConfig:
    """The Sprint-5 default: weight 1.0 on the keyword category, no role override."""
    return ScoringConfig(
        role_level="mid",
        weights={"keyword": 1.0},
    )


__all__ = [
    "ScoringEngine",
    "default_scoring_engine",
    "derive_rating",
    "keyword_only_config",
]
