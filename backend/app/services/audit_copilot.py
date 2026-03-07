"""
Audit Questions / Inspection Copilot
=====================================

Answers bounded audit readiness questions grounded in study-specific data:
  - compliance flags
  - deviation signals
  - inspection simulation outputs
  - site enrollment and activation state

Question routing uses keyword matching against a small set of bounded
categories. If OPENAI_API_KEY is configured, answers are enhanced via GPT-4o.
"""
import logging
import re
from collections import Counter
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import ComplianceFlag, DeviationSignal, InspectionSimulation, Site, Study

logger = logging.getLogger("centitmf.audit")

# ---------------------------------------------------------------------------
# Question routing
# ---------------------------------------------------------------------------

_ROUTE_PATTERNS = [
    ("highest_risk",  re.compile(r"highest.risk|most.risk|riskiest|worst.site|top.risk|at.risk", re.I)),
    ("missing",       re.compile(r"missing|artifact|document|what.need|not.on.file|incomplete|gaps", re.I)),
    ("fix_first",     re.compile(r"fix.first|priorit|remedia|action|address|should.do|most.important|where.start|next.step", re.I)),
    ("score_drivers", re.compile(r"driving|score.down|why.low|causing|deduct|penalt|what.affecting|bringing.down", re.I)),
    ("site_detail",   re.compile(r"site\s+\d+|why.is.site|site.risk|about.site", re.I)),
    ("overall",       re.compile(r"ready|readiness|overall|summary|status|assessment|how.is|state.of", re.I)),
]


def _route_question(question: str) -> str:
    for category, pattern in _ROUTE_PATTERNS:
        if pattern.search(question):
            return category
    return "overall"


# ---------------------------------------------------------------------------
# Context loader
# ---------------------------------------------------------------------------

async def _load_context(db: AsyncSession, study_id: str) -> dict[str, Any] | None:
    study = await db.get(Study, study_id)
    if not study:
        return None

    sites_result = await db.execute(select(Site).where(Site.study_id == study_id))
    sites = list(sites_result.scalars().all())

    flags_result = await db.execute(select(ComplianceFlag).where(ComplianceFlag.study_id == study_id))
    flags = list(flags_result.scalars().all())

    dev_result = await db.execute(select(DeviationSignal).where(DeviationSignal.study_id == study_id))
    dev_signals = list(dev_result.scalars().all())

    sim_result = await db.execute(
        select(InspectionSimulation)
        .where(InspectionSimulation.study_id == study_id)
        .order_by(InspectionSimulation.created_at.desc())
        .limit(1)
    )
    sim = sim_result.scalars().first()

    flag_counts: Counter = Counter(f.site_id for f in flags if f.site_id)
    high_counts: Counter = Counter(
        f.site_id for f in flags if f.site_id and f.severity in ("HIGH", "CRITICAL")
    )
    dev_scores: dict[str, float] = {}
    dev_findings: dict[str, list[str]] = {}
    for sig in dev_signals:
        if sig.site_id and (sig.site_id not in dev_scores or sig.score > dev_scores[sig.site_id]):
            dev_scores[sig.site_id] = sig.score
            dev_findings[sig.site_id] = (sig.top_findings_json or {}).get("findings", [])

    return {
        "study": study,
        "sites": sites,
        "flags": flags,
        "flag_counts": flag_counts,
        "high_counts": high_counts,
        "dev_scores": dev_scores,
        "dev_findings": dev_findings,
        "site_code_map": {s.id: s.site_code for s in sites},
        "sim": sim,
    }


# ---------------------------------------------------------------------------
# Deterministic answer builders
# ---------------------------------------------------------------------------

def _answer_highest_risk(ctx: dict) -> tuple[str, list[str]]:
    sites = ctx["sites"]
    flag_counts = ctx["flag_counts"]
    high_counts = ctx["high_counts"]
    dev_scores = ctx["dev_scores"]

    if not sites:
        return "No sites found for this study.", []

    scored = sorted(
        sites,
        key=lambda s: high_counts.get(s.id, 0) * 10 + dev_scores.get(s.id, 0) * 0.5,
        reverse=True,
    )
    lines = ["Sites ranked by risk (high/critical flags + deviation score):\n"]
    basis = []
    for i, site in enumerate(scored[:3], 1):
        hf = high_counts.get(site.id, 0)
        tf = flag_counts.get(site.id, 0)
        dev = dev_scores.get(site.id)
        dev_str = f", deviation score {dev:.0f}" if dev is not None else ""
        lines.append(f"{i}. Site {site.site_code} — {hf} high/critical flags, {tf} total flags{dev_str}")
        basis.append(f"Site {site.site_code}: {tf} flags ({hf} high/critical)")

    top = scored[0]
    top_flags = [
        f for f in ctx["flags"] if f.site_id == top.id and f.severity in ("HIGH", "CRITICAL")
    ][:3]
    if top_flags:
        lines.append(f"\nKey issues at Site {top.site_code}:")
        for flag in top_flags:
            lines.append(f"  • {flag.title}")

    return "\n".join(lines), basis


def _answer_missing(ctx: dict) -> tuple[str, list[str]]:
    flags = ctx["flags"]
    site_code_map = ctx["site_code_map"]

    # TMF-001 through TMF-009 represent missing artifact rules (TMF-010 = unsigned docs)
    missing_flags = sorted(
        [f for f in flags if f.rule_code and f.rule_code != "TMF-010"],
        key=lambda f: f.risk_points,
        reverse=True,
    )
    if not missing_flags:
        return "No missing artifact issues detected. The TMF appears to have complete coverage.", []

    by_artifact: dict[str, list[str]] = {}
    for flag in missing_flags:
        key = flag.title.split(" for Site")[0].strip()
        site_code = site_code_map.get(flag.site_id, "Study") if flag.site_id else "Study"
        by_artifact.setdefault(key, []).append(f"Site {site_code}")

    lines = [f"{len(missing_flags)} missing artifact issues across {len(by_artifact)} artifact types:\n"]
    for artifact, affected_sites in list(by_artifact.items())[:8]:
        lines.append(f"• {artifact} — {', '.join(affected_sites[:3])}")

    return "\n".join(lines), [f"{len(missing_flags)} missing artifact compliance flags"]


def _answer_fix_first(ctx: dict) -> tuple[str, list[str]]:
    flags = ctx["flags"]
    site_code_map = ctx["site_code_map"]

    if not flags:
        return "No active compliance flags. The TMF appears to be in good standing.", []

    top = sorted(flags, key=lambda f: f.risk_points, reverse=True)[:6]
    lines = ["Prioritized remediation actions by risk impact:\n"]
    for i, flag in enumerate(top, 1):
        site_code = site_code_map.get(flag.site_id, "Study") if flag.site_id else "Study"
        lines.append(f"{i}. [{flag.severity}] {flag.title} (−{flag.risk_points} pts) — Site {site_code}")

    return "\n".join(lines), [f"Ranked by risk_points; {len(flags)} total active flags"]


def _answer_score_drivers(ctx: dict) -> tuple[str, list[str]]:
    sim = ctx.get("sim")
    flags = ctx["flags"]

    if sim and sim.results_json:
        bd = sim.results_json.get("scoring_breakdown", {})
        score = sim.risk_score
        lines = [
            f"Readiness score: {score:.0f} / 100. Score deductions:\n",
            f"  Flag deductions:      −{bd.get('flag_deduction', 0)} pts",
        ]
        if bd.get("cluster_penalty", 0):
            lines.append(f"  Site cluster penalty: −{bd.get('cluster_penalty', 0)} pts")
        dev_pen = bd.get("multi_site_deviation_penalty", 0) + bd.get("per_site_deviation_penalty", 0)
        if dev_pen:
            lines.append(f"  Deviation penalties:  −{dev_pen} pts")
        lines.append(f"\n  Total deducted: −{bd.get('total_deduction', 0)} pts from base of 100.")
        return "\n".join(lines), [f"Latest simulation (score: {score:.0f})"]

    total_deduction = sum(f.risk_points for f in flags)
    high_count = sum(1 for f in flags if f.severity in ("HIGH", "CRITICAL"))
    lines = [
        "No simulation run yet. Based on active compliance flags:\n",
        f"  {len(flags)} flags contributing an estimated −{total_deduction} pts",
        f"  {high_count} HIGH or CRITICAL severity flags",
        "\nRun an inspection simulation for the full breakdown.",
    ]
    return "\n".join(lines), [f"{len(flags)} flags, ~{total_deduction} pts estimated deduction"]


def _answer_site_detail(ctx: dict, question: str) -> tuple[str, list[str]]:
    m = re.search(r"site\s+(\d+)", question, re.I)
    code = m.group(1) if m else None
    sites = ctx["sites"]
    flags = ctx["flags"]

    if code:
        target = next((s for s in sites if s.site_code == code), None)
        if not target:
            return f"Site {code} not found in this study.", []
    else:
        target = max(
            sites,
            key=lambda s: ctx["high_counts"].get(s.id, 0) * 10 + ctx["flag_counts"].get(s.id, 0),
            default=None,
        ) if sites else None
        if not target:
            return "No sites found in this study.", []

    site_flags = [f for f in flags if f.site_id == target.id]
    dev = ctx["dev_scores"].get(target.id)
    findings = ctx["dev_findings"].get(target.id, [])
    high_flags = [f for f in site_flags if f.severity in ("HIGH", "CRITICAL")]

    lines = [f"Site {target.site_code} risk analysis:\n"]
    lines.append(f"  Enrolled: {target.enrolled_count} patients")
    lines.append(f"  Total compliance flags: {len(site_flags)} ({len(high_flags)} high/critical)")
    if dev is not None:
        lines.append(f"  Deviation risk score: {dev:.0f} / 100")

    if high_flags:
        lines.append("\nHigh-priority issues:")
        for flag in high_flags[:4]:
            lines.append(f"  • [{flag.severity}] {flag.title}")
    if findings:
        lines.append("\nDeviation signals:")
        for finding in findings[:3]:
            lines.append(f"  • {finding}")

    return "\n".join(lines), [f"Site {target.site_code}: {len(site_flags)} flags"]


def _answer_overall(ctx: dict) -> tuple[str, list[str]]:
    sim = ctx.get("sim")
    flags = ctx["flags"]
    sites = ctx["sites"]
    high_flags = [f for f in flags if f.severity in ("HIGH", "CRITICAL")]

    if sim:
        zone_desc = {
            "LOW": "This study is in good inspection readiness condition with minor gaps.",
            "MEDIUM": "This study has moderate readiness concerns that should be addressed before inspection.",
            "HIGH": "This study has significant readiness deficiencies requiring prompt remediation.",
            "CRITICAL": "This study would likely fail a regulatory inspection in its current state.",
        }
        zone = sim.vulnerable_zone or "MEDIUM"
        lines = [
            f"Inspection Readiness Score: {sim.risk_score:.0f} / 100 — {zone} RISK\n",
            zone_desc.get(zone, ""),
            f"\n  {len(flags)} total compliance flags ({len(high_flags)} high/critical)",
            f"  {len(sites)} sites",
        ]
        return "\n".join(lines), [f"Simulation score: {sim.risk_score:.0f}, zone: {zone}"]

    lines = [
        "No inspection simulation run yet.\n",
        f"  {len(flags)} compliance flags detected ({len(high_flags)} high/critical)",
        f"  {len(sites)} sites on record",
        "\nRun an inspection simulation to generate a full readiness score and narrative.",
    ]
    return "\n".join(lines), [f"{len(flags)} flags, no simulation"]


# ---------------------------------------------------------------------------
# LLM enhancement
# ---------------------------------------------------------------------------

async def _llm_enhance(question: str, base_answer: str, ctx: dict) -> str:
    from openai import AsyncOpenAI

    flags = ctx["flags"]
    sim = ctx.get("sim")
    high_flags = [f for f in flags if f.severity in ("HIGH", "CRITICAL")][:5]
    score_info = f"Score: {sim.risk_score:.0f}/100 ({sim.vulnerable_zone})" if sim else "No simulation"
    flag_summary = "\n".join(
        f"- [{f.severity}] {f.title}" for f in high_flags
    ) or "None"

    prompt = f"""You are a regulatory compliance specialist for clinical trial inspection readiness.

Study context:
{score_info}
Total flags: {len(flags)} ({len(high_flags)} high/critical)
Top issues:
{flag_summary}

User question: {question}

Base analysis:
{base_answer}

Provide a concise, enhanced answer (3–5 sentences). Be direct and actionable. No hedging."""

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
        temperature=0.2,
    )
    return response.choices[0].message.content or base_answer


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def answer_audit_question(
    db: AsyncSession,
    study_id: str,
    question: str,
) -> dict[str, Any]:
    ctx = await _load_context(db, study_id)
    if not ctx:
        return {
            "question": question,
            "answer": "Study not found or no data available.",
            "data_basis": [],
        }

    category = _route_question(question)
    if category == "highest_risk":
        answer, basis = _answer_highest_risk(ctx)
    elif category == "missing":
        answer, basis = _answer_missing(ctx)
    elif category == "fix_first":
        answer, basis = _answer_fix_first(ctx)
    elif category == "score_drivers":
        answer, basis = _answer_score_drivers(ctx)
    elif category == "site_detail":
        answer, basis = _answer_site_detail(ctx, question)
    else:
        answer, basis = _answer_overall(ctx)

    if settings.has_openai:
        try:
            answer = await _llm_enhance(question, answer, ctx)
        except Exception as e:
            logger.warning(f"LLM enhancement failed, using deterministic answer: {e}")

    return {"question": question, "answer": answer, "data_basis": basis}
