import json
from pydantic import BaseModel, field_validator
from services.llm_client import chat_complete


SYSTEM = """You are a resume parsing specialist. Extract structured data from the resume text below.
Return ONLY valid JSON. No commentary, no markdown, no code fences.

CRITICAL rules for roles:
- List each job as a SEPARATE object. If someone held two titles at the same company (e.g. SDE-1 then SDE-2), they are TWO separate role objects.
- "duration_months" MUST be computed from the explicit date range on the resume (e.g. "Jan 2025 – March 2026" = 14 months). NEVER copy a number from a summary sentence like "3.5 years experience" — that is total experience, not a single role's duration.
- If the end date is "Present" or missing, use the current month (April 2026) to calculate duration.
- "start_year" and "end_year" are the calendar year integers. end_year is null if the role is current.
- "duration_months" must be an INTEGER (whole number). Round to nearest month.
- Do NOT invent dates. If a date range is not explicitly stated, set duration_months to 0.

Schema:
{
  "name": "string",
  "email": "string or empty",
  "location": "string or empty",
  "roles": [
    {
      "title": "string — exact job title as written",
      "company": "string — exact company name as written",
      "duration_months": integer — computed from explicit date range,
      "start_year": integer,
      "end_year": integer or null,
      "description": "string — one sentence summary of key work"
    }
  ],
  "skills": ["string"],
  "education": [{"degree": "string", "field": "string", "institution": "string", "year": integer or null}],
  "tenure_years": float — total years of professional experience (sum of non-overlapping full-time roles, excluding internships),
  "seniority": "intern|junior|mid|senior|staff|lead|executive",
  "domain": "string — primary professional domain",
  "key_achievements": ["string — specific, quantified achievements from the resume"]
}"""


class ResumeProfile(BaseModel):
    name: str = ""
    email: str = ""
    location: str = ""
    roles: list[dict] = []
    skills: list[str] = []
    education: list[dict] = []
    tenure_years: float = 0.0
    seniority: str = "mid"
    domain: str = ""
    key_achievements: list[str] = []

    @field_validator("seniority")
    @classmethod
    def validate_seniority(cls, v):
        valid = {"intern", "junior", "mid", "senior", "staff", "lead", "executive"}
        return v if v in valid else "mid"


def extract(resume_text: str, max_retries: int = 3) -> ResumeProfile:
    """EXTRACTOR agent: parses raw resume text into a structured ResumeProfile."""
    messages = [{"role": "user", "content": f"Parse this resume:\n\n{resume_text}"}]

    for attempt in range(max_retries):
        try:
            raw = chat_complete(messages, system=SYSTEM, json_mode=True)
            data = json.loads(raw)
            return ResumeProfile(**data)
        except (json.JSONDecodeError, Exception) as e:
            if attempt == max_retries - 1:
                raise ValueError(f"EXTRACTOR failed after {max_retries} attempts: {e}")
            messages.append({"role": "assistant", "content": raw if "raw" in dir() else ""})
            messages.append({
                "role": "user",
                "content": f"The JSON was invalid: {e}. Please return valid JSON only."
            })
    raise ValueError("EXTRACTOR failed")
