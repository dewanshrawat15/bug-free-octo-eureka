from services.llm_client import chat_stream, chat_complete
from services.agents.extractor import ResumeProfile
from typing import Iterator
import json


SYSTEM = """You are a sharp career coach writing a CHAT MESSAGE — not an email, not a letter.

Rules:
1. Reference at least 2 SPECIFIC facts from their resume (company names, exact tenures, specific achievements)
2. Name ONE real tension or opportunity visible in their background (e.g., fast growth but no senior title, switching domains, approaching a ceiling)
3. Keep it to 3-4 sentences maximum
4. Do NOT be generic. "You have a strong background" is not acceptable.
5. End with an open question that invites them to share their direction
6. Tone: direct, warm, like a smart mentor who actually read the resume
7. NEVER add a sign-off. No "Best,", no "Regards,", no "[Your Name]", no closing phrase. Just stop after the question.
8. CRITICAL accuracy rule: Never merge roles across different companies. Each role entry lists the EXACT company. Do NOT say someone "rose from intern to senior at Company X" unless BOTH roles are at Company X. If the internship is at Company A and later roles are at Company B, they are separate employers.
9. Tenures are given as human-readable strings (e.g. "1 year 3 months"). Use them exactly — do not convert or reinterpret."""


def generate_stream(profile: ResumeProfile, persona: str) -> Iterator[str]:
    """OPENING_GENERATOR agent: streams personalized opening message tokens."""
    prompt = _build_prompt(profile, persona)
    messages = [{"role": "user", "content": prompt}]
    yield from chat_stream(messages, system=SYSTEM)


def generate(profile: ResumeProfile, persona: str) -> str:
    """OPENING_GENERATOR agent: returns full opening message."""
    prompt = _build_prompt(profile, persona)
    messages = [{"role": "user", "content": prompt}]
    return chat_complete(messages, system=SYSTEM)


def _fmt_duration(months) -> str:
    try:
        m = int(round(float(months)))
    except (TypeError, ValueError):
        return str(months)
    years, rem = divmod(m, 12)
    if years and rem:
        return f"{years} year{'s' if years > 1 else ''} {rem} month{'s' if rem > 1 else ''}"
    elif years:
        return f"{years} year{'s' if years > 1 else ''}"
    return f"{rem} month{'s' if rem > 1 else ''}"


def _build_prompt(profile: ResumeProfile, persona: str) -> str:
    recent_role = profile.roles[0] if profile.roles else {}
    achievements = profile.key_achievements[:3]
    roles_readable = [
        {
            "title": r.get("title"),
            "company": r.get("company"),
            "tenure": _fmt_duration(r.get("duration_months", 0)),
        }
        for r in profile.roles
    ]
    return (
        f"Persona: {persona}\n"
        f"Name: {profile.name}\n"
        f"Current role: {recent_role.get('title', 'N/A')} at {recent_role.get('company', 'N/A')}\n"
        f"Total experience: {profile.tenure_years:.1f} years\n"
        f"Domain: {profile.domain}\n"
        f"Seniority: {profile.seniority}\n"
        f"Key achievements: {json.dumps(achievements)}\n"
        f"All roles (each at the company listed, tenures are exact):\n{json.dumps(roles_readable, indent=2)}\n\n"
        f"Write the opening chat message for this {persona} persona user. No sign-off."
    )
