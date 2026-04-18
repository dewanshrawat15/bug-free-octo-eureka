import json
from services.llm_client import chat_complete
from services.agents.extractor import ResumeProfile


SYSTEM = """You detect career persona from a resume profile. Classify into exactly one of:
- Pivot: ~2-4 years experience, signalling desire to change function/domain
- Grow: 4+ years, solid performer in same domain wanting to level up
- Graduate: <=1 year experience or recent graduate, overwhelmed by options

Rules:
- tenure_years < 1.5 => Graduate (unless very senior roles)
- tenure_years >= 1.5 and tenure_years < 4 => likely Pivot
- tenure_years >= 4 and same domain across roles => Grow
- multiple domains in roles history => Pivot

Return ONLY valid JSON: {"persona": "Pivot|Grow|Graduate", "reasoning": "one sentence"}"""


def detect(profile: ResumeProfile) -> tuple[str, str]:
    """PERSONA_DETECTOR agent: returns (persona, reasoning)."""
    profile_summary = {
        "tenure_years": profile.tenure_years,
        "seniority": profile.seniority,
        "domain": profile.domain,
        "role_titles": [r.get("title", "") for r in profile.roles],
        "education": [e.get("degree", "") for e in profile.education],
    }
    messages = [{"role": "user", "content": f"Classify this profile:\n{json.dumps(profile_summary)}"}]
    raw = chat_complete(messages, system=SYSTEM, json_mode=True)
    try:
        data = json.loads(raw)
        persona = data.get("persona", "Grow")
        reasoning = data.get("reasoning", "")
        if persona not in ("Pivot", "Grow", "Graduate"):
            persona = "Grow"
        return persona, reasoning
    except Exception:
        return _rule_based(profile), "Rule-based fallback"


def _rule_based(profile: ResumeProfile) -> str:
    if profile.tenure_years < 1.5:
        return "Graduate"
    if profile.tenure_years < 4:
        return "Pivot"
    return "Grow"
