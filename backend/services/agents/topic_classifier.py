import json
from services.llm_client import chat_complete


SYSTEM = """You are a topic classifier for a career coaching assistant.
Determine if the user's message is career-related.

Career-related (return true): jobs, career paths, skills, salary, job search,
resumes, interviews, promotions, career transitions, professional development,
networking, industries, companies, roles, timelines for career goals, learning plans,
follow-up questions about a career plan or path, questions about next steps in a career,
anything about becoming a specific role or improving professionally, work experience,
job titles like SDE, PM, CTO, engineer, manager, etc.

When in doubt, lean toward career_related: true. Only return false if the message is
CLEARLY unrelated to careers (e.g. "what is the capital of France?", recipes, sports scores,
movies, personal relationships with no career angle).

Return ONLY valid JSON: {"career_related": true|false, "confidence": 0.0-1.0}"""


OFF_TOPIC_REPLY = (
    "I'm focused on helping you navigate your career. "
    "Is there something about your next move, skill gaps, or career direction you'd like to explore?"
)


def classify(message: str) -> tuple[bool, float]:
    """TOPIC_CLASSIFIER agent: returns (is_career_related, confidence)."""
    messages = [{"role": "user", "content": message}]
    try:
        raw = chat_complete(messages, system=SYSTEM, json_mode=True)
        data = json.loads(raw)
        return bool(data.get("career_related", True)), float(data.get("confidence", 0.5))
    except Exception:
        return True, 0.5
