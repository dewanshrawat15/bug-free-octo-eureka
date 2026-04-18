import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from temporalio import activity
from services.resume_parser import extract_text
from services.agents import extractor, persona_detector, opening_generator, path_generator


@activity.defn
async def activity_extract_resume(resume_path: str) -> dict:
    text = extract_text(resume_path)
    profile = extractor.extract(text)
    return profile.model_dump()


@activity.defn
async def activity_detect_persona(profile_dict: dict) -> dict:
    profile = extractor.ResumeProfile(**profile_dict)
    persona, reasoning = persona_detector.detect(profile)
    return {"persona": persona, "reasoning": reasoning}


@activity.defn
async def activity_generate_opening(profile_dict: dict, persona: str) -> str:
    profile = extractor.ResumeProfile(**profile_dict)
    return opening_generator.generate(profile, persona)


@activity.defn
async def activity_generate_paths(
    profile_dict: dict,
    persona: str,
    alive_moments: list,
    friction_points: list,
    direction: str,
    geography: str,
    round_number: int,
    rejected_paths: list,
    aspiration: str,
) -> list:
    profile = extractor.ResumeProfile(**profile_dict)
    cards = path_generator.generate(
        profile=profile,
        persona=persona,
        alive_moments=alive_moments,
        friction_points=friction_points,
        direction=direction,
        geography=geography,
        round_number=round_number,
        rejected_paths=rejected_paths,
        aspiration=aspiration,
    )
    return [c.model_dump() for c in cards]
