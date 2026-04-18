import json
import re
from services.llm_client import chat_complete, chat_stream
from services.agents.extractor import ResumeProfile
from typing import Iterator

_PATH_REQUEST_PATTERNS = re.compile(
    r"\b(want to (become|pursue|be|get|achieve|work as)|"
    r"create (a )?path (for|to)|make (a )?path|"
    r"help (me )?(become|pursue|get to)|"
    r"pursuing|aspire to|aiming (for|to become)|"
    r"goal is to become|interested in becoming)\b",
    re.IGNORECASE,
)


ROUTER_SYSTEM = """You classify career coaching messages into intents.
Return ONLY valid JSON: {"intent": "deepen|path_request|regenerate|free_career|off_topic", "aspiration": "string or null"}

intents:
- deepen: user wants to go deeper on a specific path already shown (e.g. "tell me more about path 1", "what would week 1 look like for the PM path")
- path_request: user explicitly asks to pursue, become, or get a path card for a specific role (e.g. "I want to become SDE 3", "create a path for engineering manager", "make me a path for product manager", "I want to pursue X role")
- regenerate: user wants different paths (e.g. "show me different options", "none of these feel right")
- free_career: any other career question (skills, timeline, salary, transitions, market questions)
- off_topic: not career related

For path_request, set "aspiration" to the exact role the user wants (e.g. "SDE 3", "Engineering Manager", "Product Manager")."""

CAREER_SYSTEM = """You are a direct, expert career coach. Answer the user's career question concisely.
Reference their specific background when relevant. Keep answers under 200 words unless a detailed plan is asked for.
Stay focused on career topics only."""


def classify_intent(message: str) -> tuple[str, str | None]:
    """CONVERSATION_ROUTER: classifies message intent and extracts aspiration if any."""
    try:
        raw = chat_complete(
            [{"role": "user", "content": message}],
            system=ROUTER_SYSTEM,
            json_mode=True,
        )
        data = json.loads(raw)
        intent = data.get("intent", "free_career")
        aspiration = data.get("aspiration") or None
        if intent not in ("deepen", "path_request", "regenerate", "free_career", "off_topic"):
            intent = "free_career"
        # LLM often misses path_request — promote if aspiration extracted + keywords match
        if intent == "free_career" and aspiration and _PATH_REQUEST_PATTERNS.search(message):
            intent = "path_request"
        return intent, aspiration
    except Exception:
        return "free_career", None


def respond_path_request(
    aspiration: str,
    profile: ResumeProfile,
    message: str,
) -> Iterator[str]:
    """Streams a short intro then yields a sentinel so the caller can attach a path card."""
    context = (
        f"User profile: {profile.name}, {profile.tenure_years:.1f} years in {profile.domain}, "
        f"current seniority: {profile.seniority}. "
        f"Recent role: {profile.roles[0].get('title', '') if profile.roles else 'N/A'} "
        f"at {profile.roles[0].get('company', '') if profile.roles else 'N/A'}."
    )
    system = (
        CAREER_SYSTEM
        + f"\n\nUser background: {context}"
        + f"\n\nThe user wants to pursue: {aspiration}. "
        "Write 2 sentences max acknowledging their goal and what makes them a good fit for it. "
        "Then stop — a path card will be shown below your message."
    )
    messages = [{"role": "user", "content": message}]
    yield from chat_stream(messages, system=system)


def respond_stream(
    message: str,
    profile: ResumeProfile,
    conversation_history: list[dict],
) -> Iterator[str]:
    """Streams a career response to a free-text message, grounded in the user's profile."""
    context = (
        f"User profile: {profile.name}, {profile.tenure_years:.1f} years in {profile.domain}, "
        f"current seniority: {profile.seniority}. "
        f"Recent role: {profile.roles[0].get('title', '') if profile.roles else 'N/A'} "
        f"at {profile.roles[0].get('company', '') if profile.roles else 'N/A'}."
    )
    system = CAREER_SYSTEM + f"\n\nUser background: {context}"
    messages = conversation_history[-6:] + [{"role": "user", "content": message}]
    yield from chat_stream(messages, system=system)
