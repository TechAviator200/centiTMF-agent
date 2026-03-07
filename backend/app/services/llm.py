"""
LLM Narrative Service
=====================

Generates inspection readiness narrative.
Uses GPT-4o when OPENAI_API_KEY is set; falls back to deterministic template.

Score interpretation (readiness model):
  80-100: LOW RISK — strong readiness
  60-79:  MEDIUM RISK — some gaps
  40-59:  HIGH RISK — significant concerns
  0-39:   CRITICAL RISK — likely to fail inspection
"""
import logging
from typing import Any

from app.core.config import settings

logger = logging.getLogger("centitmf.llm")


def _deterministic_narrative(score: float, results: dict[str, Any]) -> str:
    missing = results.get("missing_artifacts", [])
    top_flags = results.get("top_flags", [])
    dev_sites = results.get("high_deviation_sites", [])
    breakdown = results.get("scoring_breakdown", {})

    total_flags = results.get("total_flags", 0)
    high_flags = results.get("high_flags", 0)
    critical_flags = results.get("critical_flags", 0)

    if score >= 80:
        readiness_band = "LOW RISK"
        exec_summary = (
            "This trial's TMF is in good inspection readiness condition. "
            "Minor compliance gaps exist but do not represent material regulatory risk. "
            "Continue current monitoring and document management practices."
        )
    elif score >= 60:
        readiness_band = "MEDIUM RISK"
        exec_summary = (
            "This trial has moderate inspection readiness concerns. "
            "Several compliance gaps have been identified that should be addressed before "
            "any regulatory inspection. Prioritize resolving HIGH-severity flags within 30 days."
        )
    elif score >= 40:
        readiness_band = "HIGH RISK"
        exec_summary = (
            "This trial presents significant inspection readiness deficiencies. "
            "Multiple HIGH-severity compliance flags indicate substantial TMF gaps. "
            "Immediate remediation action is required. A for-cause audit is recommended "
            "before scheduling any regulatory inspection."
        )
    else:
        readiness_band = "CRITICAL RISK"
        exec_summary = (
            "This trial would likely fail a regulatory inspection in its current state. "
            "Critical TMF artifacts are missing across multiple sites, and deviation patterns "
            "suggest systemic protocol compliance failures. Immediate sponsor intervention is required. "
            "All site activities should be reviewed before proceeding."
        )

    lines = [
        "INSPECTION READINESS ASSESSMENT",
        f"Readiness Score: {score:.0f} / 100 — {readiness_band}",
        f"Total Flags: {total_flags}  |  High: {high_flags}  |  Critical: {critical_flags}",
        "",
        "EXECUTIVE SUMMARY",
        exec_summary,
    ]

    if breakdown:
        lines += [
            "",
            "SCORING BREAKDOWN",
            f"  Base score:                100",
            f"  Flag deductions:           -{breakdown.get('flag_deduction', 0)}",
            f"  Site cluster penalties:    -{breakdown.get('cluster_penalty', 0)}",
            f"  Multi-site deviation:      -{breakdown.get('multi_site_deviation_penalty', 0)}",
            f"  Per-site deviation:        -{breakdown.get('per_site_deviation_penalty', 0)}",
            f"  ─────────────────────────────",
            f"  Final readiness score:     {score:.0f}",
        ]

    if missing:
        lines += ["", "MISSING ARTIFACTS (TOP FINDINGS)"]
        for item in missing[:6]:
            lines.append(f"  • {item}")

    if top_flags:
        lines += ["", "TOP COMPLIANCE FLAGS"]
        for flag in top_flags[:6]:
            site_label = f"Site {flag.get('site_code', '?')}"
            lines.append(
                f"  [{flag.get('severity', 'N/A')}] {flag.get('title', '')} — {site_label}"
            )

    if dev_sites:
        lines += ["", "HIGH-DEVIATION SITES"]
        for site in dev_sites[:3]:
            lines.append(f"  • Site {site}")

    lines += [
        "",
        "RECOMMENDED ACTIONS",
        "1. Obtain missing HIGH-severity artifacts immediately (target: 14 days).",
        "2. Conduct for-cause monitoring visit at highest-risk sites.",
        "3. Verify all delegation logs reflect current site staff.",
        "4. Ensure all regulatory documents bear required signatures.",
        "5. Conduct internal mock inspection 30 days before scheduled regulatory review.",
    ]

    return "\n".join(lines)


async def generate_inspection_narrative(
    risk_score: float, results: dict[str, Any]
) -> str:
    if settings.has_openai:
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

            flags_summary = "\n".join(
                f"- [{f.get('severity')}] {f.get('title')} (Site {f.get('site_code', '?')})"
                for f in results.get("top_flags", [])[:8]
            )
            dev_sites = ", ".join(results.get("high_deviation_sites", [])[:3]) or "None"

            prompt = f"""You are a senior regulatory affairs specialist reviewing a clinical trial TMF inspection readiness report.

Readiness Score: {risk_score:.0f} / 100 (higher = better; 80+ = inspection ready)
Total Compliance Flags: {results.get('total_flags', 0)} ({results.get('high_flags', 0)} HIGH, {results.get('critical_flags', 0)} CRITICAL)
High-Deviation Sites: {dev_sites}

Top Findings:
{flags_summary}

Write a 3-paragraph inspection readiness narrative for the sponsor's quality leadership team.
Paragraph 1: Overall readiness assessment and risk zone.
Paragraph 2: Top 3 vulnerabilities with specific detail.
Paragraph 3: Prioritized remediation actions (numbered list).
Tone: direct, clinical, enterprise-grade. No hedging."""

            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=600,
                temperature=0.2,
            )
            text = response.choices[0].message.content
            if text:
                return text
        except Exception as e:
            logger.warning(f"OpenAI narrative failed, using deterministic fallback: {e}")

    return _deterministic_narrative(risk_score, results)
