import json
import uuid
from pydantic import BaseModel
from services.llm_client import chat_complete
from services.agents.extractor import ResumeProfile

PATH_CARD_KEYS = {"role", "company_type", "salary_range", "why_you_fit"}

SYSTEM_ONE = """You are a career path generator. Generate ONE career path card as a JSON object.

Rules:
- why_you_fit MUST reference the user's specific company names or achievements from their resume
- skills_you_have must only list skills actually in their resume
- skills_gap must be skills they do NOT currently have
- salary_range should be realistic for the Indian market unless geography says otherwise
- Be specific: name real company types, real timelines

BRIDGE PATH RULE (CRITICAL):
If the aspiration is outside the user's current domain (e.g. a software engineer wanting to be a music teacher,
artist, chef, athlete), you MUST generate a BRIDGE path — a role that:
1. Uses their existing technical skills as a genuine advantage
2. Moves meaningfully toward the aspiration
Examples for a software engineer wanting music teaching:
  - "EdTech Engineer at music learning platform (e.g. Fender Play, Simply Piano)"
  - "CTO / Tech Lead at music education startup"
  - "Audio Software Engineer building music teaching tools"
  - "Product Engineer at music streaming/discovery platform"
NEVER generate a generic tech role that ignores the aspiration.
The role name and why_you_fit MUST clearly reference the aspiration domain.

Return ONLY a JSON object (no array, no wrapper):
{
  "id": "unique-string",
  "role": "exact job title",
  "company_type": "e.g. Series B SaaS startup",
  "salary_range": "e.g. Rs 28L - Rs 42L",
  "why_you_fit": "specific reason referencing their background AND how it connects to the aspiration",
  "skills_you_have": ["skill1", "skill2"],
  "skills_gap": ["skill1", "skill2"],
  "transition_timeline": "e.g. 0-3 months, direct transition",
  "market_demand": "e.g. High — 200+ open roles in Bangalore",
  "target_country": null,
  "visa_notes": null
}"""


class PathCard(BaseModel):
    id: str
    role: str
    company_type: str
    salary_range: str
    why_you_fit: str
    skills_you_have: list[str] = []
    skills_gap: list[str] = []
    transition_timeline: str = ""
    market_demand: str = ""
    target_country: str | None = None
    visa_notes: str | None = None


def generate(
    profile: ResumeProfile,
    persona: str,
    alive_moments: list[str],
    friction_points: list[str],
    direction: str,
    geography: str,
    round_number: int,
    rejected_paths: list[dict],
    aspiration: str = "",
) -> list[PathCard]:
    """PATH_GENERATOR: calls LLM once per card (3 calls) for reliability with small models."""
    base_context = _build_context(
        profile, persona, alive_moments, friction_points,
        direction, geography, round_number, rejected_paths, aspiration
    )
    cards = []
    generated_roles = []

    for slot in range(1, 4):
        card = _generate_one(base_context, slot, generated_roles, round_number)
        cards.append(card)
        generated_roles.append(card.role)

    return cards


def _generate_one(context: str, slot: int, already_generated: list[str], round_number: int, max_retries: int = 3) -> PathCard:
    avoid = ""
    if already_generated:
        avoid = f"\nAvoid these roles already generated this round: {json.dumps(already_generated)}"

    prompt = f"{context}{avoid}\n\nGenerate career path card #{slot} of 3. Make it genuinely different from any cards already generated."
    messages = [{"role": "user", "content": prompt}]

    raw = ""
    for attempt in range(max_retries):
        try:
            raw = chat_complete(messages, system=SYSTEM_ONE, json_mode=True)
            data = _extract_dict(raw)
            if "id" not in data or not data["id"]:
                data["id"] = f"path-r{round_number}-{slot}"
            # coerce id to string
            data["id"] = str(data["id"])
            # coerce list fields
            for field in ("skills_you_have", "skills_gap"):
                if isinstance(data.get(field), str):
                    data[field] = [s.strip() for s in data[field].split(",") if s.strip()]
            # coerce transition_timeline to string
            if isinstance(data.get("transition_timeline"), list):
                data["transition_timeline"] = ", ".join(
                    str(t.get("description", t)) if isinstance(t, dict) else str(t)
                    for t in data["transition_timeline"]
                )
            return PathCard(**data)
        except Exception as e:
            print(f"[PATH_GENERATOR slot={slot} attempt={attempt+1}] error={e!r} raw={raw[:200]!r}")
            if attempt == max_retries - 1:
                raise ValueError(f"PATH_GENERATOR failed for slot {slot}: {e}")
            messages.append({"role": "assistant", "content": raw})
            messages.append({
                "role": "user",
                "content": (
                    f"That response had an error: {e}. "
                    "Return ONLY a single JSON object with these exact keys: "
                    "id, role, company_type, salary_range, why_you_fit, "
                    "skills_you_have (array), skills_gap (array), transition_timeline (string), "
                    "market_demand, target_country, visa_notes."
                ),
            })
    raise ValueError(f"PATH_GENERATOR failed for slot {slot}")


def _extract_dict(raw: str) -> dict:
    """Parse a JSON dict from LLM output, handling common wrapping patterns."""
    data = json.loads(raw)
    if isinstance(data, list):
        if not data:
            raise ValueError("Empty array returned")
        data = data[0]
    if isinstance(data, dict):
        # If it looks like a path card, use it directly
        if PATH_CARD_KEYS & set(data.keys()):
            return data
        # Otherwise unwrap single-key dict containing a path card
        for v in data.values():
            if isinstance(v, dict) and PATH_CARD_KEYS & set(v.keys()):
                return v
            if isinstance(v, list) and v and isinstance(v[0], dict) and PATH_CARD_KEYS & set(v[0].keys()):
                return v[0]
    raise ValueError(f"Cannot extract path card dict from: {raw[:200]!r}")


def _build_context(profile, persona, alive_moments, friction_points, direction, geography, round_number, rejected_paths, aspiration):
    parts = [
        f"Persona: {persona}",
        f"Name: {profile.name}",
        f"Domain: {profile.domain or 'software engineering'}",
        f"Seniority: {profile.seniority}",
        f"Tenure: {profile.tenure_years:.1f} years",
        f"Skills: {json.dumps(profile.skills[:20])}",
        f"Key achievements: {json.dumps(profile.key_achievements[:5])}",
        f"Roles: {json.dumps([{'title': r.get('title'), 'company': r.get('company')} for r in profile.roles])}",
        f"What energises them: {json.dumps(alive_moments)}",
        f"What causes friction: {json.dumps(friction_points)}",
        f"Career direction: {direction}",
        f"Geography: {geography}",
        f"Round: {round_number} (1=first, 2=second, 3=final)",
    ]
    if aspiration:
        parts.append(
            f"Aspiration: {aspiration}\n"
            f"IMPORTANT: Generate a BRIDGE path that uses the user's tech skills to move toward '{aspiration}'. "
            f"The role MUST be relevant to '{aspiration}' — do not generate a generic tech role that ignores this aspiration."
        )
    if rejected_paths:
        parts.append(f"Previously rejected roles (must differ): {json.dumps([p.get('role') for p in rejected_paths])}")
    return "\n".join(parts)


def generate_targeted(profile: ResumeProfile, target_role: str) -> PathCard:
    """Generate a single path card targeted at a specific role the user asked for."""
    context = (
        f"Name: {profile.name}\n"
        f"Domain: {profile.domain or 'software engineering'}\n"
        f"Seniority: {profile.seniority}\n"
        f"Tenure: {profile.tenure_years:.1f} years\n"
        f"Skills: {json.dumps(profile.skills[:20])}\n"
        f"Key achievements: {json.dumps(profile.key_achievements[:5])}\n"
        f"Roles: {json.dumps([{'title': r.get('title'), 'company': r.get('company')} for r in profile.roles])}\n"
        f"\nThe user specifically wants to pursue: {target_role}\n"
        f"Generate a BRIDGE path card that uses their tech skills to move toward '{target_role}'. "
        f"The role name and why_you_fit MUST be relevant to '{target_role}' — not a generic tech role. "
        "why_you_fit must explain how their background bridges to this aspiration."
    )
    return _generate_one(context, 1, [], 0)
