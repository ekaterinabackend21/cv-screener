from datetime import date

from pydantic_ai import Agent
from pydantic_ai.models import Model
from pydantic_ai.usage import UsageLimits

from generation.models import CandidateBriefPlan, CandidateProfile
from generation.reference import reference_instructions
from llm import create_text_model
from settings import Settings


def validate_count(count: int) -> None:
    """Validate the supported batch sizes for resume generation."""
    if count not in {1, 3, 5, 10}:
        raise ValueError("Candidate count must be one of: 1, 3, 5, 10.")


def create_brief_planner(model: Model) -> Agent[None, CandidateBriefPlan]:
    """Build an agent that plans a varied set of fictional candidate briefs."""
    return Agent[None, CandidateBriefPlan](
        model,
        deps_type=type(None),
        output_type=CandidateBriefPlan,
        retries=2,
        instructions=(
            "Plan a varied set of fictional software and technology candidates. "
            "The same broad role may appear more than once, but avoid making many "
            "candidates near-identical: vary seniority, location, focus areas, "
            "career history and languages. Prefer at least three distinct roles "
            "when planning five or more candidates. Keep every brief concrete enough "
            "for another model to write a realistic one-page CV. Do not use real "
            "people's identities or contact details."
        ),
    )


def generate_candidate_briefs(count: int, *, settings: Settings) -> tuple[str, ...]:
    """Generate runtime briefs and convert them into prompts for profile generation."""
    validate_count(count)
    planner = create_brief_planner(create_text_model(settings))
    result = planner.run_sync(
        f"Create exactly {count} candidate briefs. Roles may repeat occasionally, "
        "but no more than two briefs should share the same role unless the batch "
        "has fewer than five candidates.",
        usage_limits=UsageLimits(request_limit=3),
    )
    briefs = result.output.candidates
    if len(briefs) != count:
        raise ValueError(f"The planner returned {len(briefs)} briefs instead of {count}.")
    role_counts: dict[str, int] = {}
    for brief in briefs:
        key = brief.role.casefold().strip()
        role_counts[key] = role_counts.get(key, 0) + 1
    if count >= 5 and max(role_counts.values(), default=0) > 2:
        raise ValueError("The planner produced too many candidates with the same role.")
    return tuple(
        f"Role: {brief.role}\n"
        f"Seniority: {brief.seniority}\n"
        f"Location: {brief.location}\n"
        f"Focus areas: {', '.join(brief.focus_areas)}\n"
        f"Languages: {', '.join(brief.languages)}\n"
        f"Career angle: {brief.career_angle}"
        for brief in briefs
    )


def create_profile_agent(model: Model) -> Agent[None, CandidateProfile]:
    """Build an agent that produces a validated, concise fictional CV profile."""
    return Agent[None, CandidateProfile](
        model,
        deps_type=type(None),
        output_type=CandidateProfile,
        retries=2,
        instructions=(
            "Create one fictional but realistic candidate CV in English from the brief. "
            "Keep it concise enough for a readable single-page A4 resume with a portrait. "
            "Use a short summary, specific responsibilities and credible achievements. "
            "Avoid inflated metrics and generic repeated accomplishments. "
            "Match seniority to the career history. List recent experience first; "
            "use internships or substantial projects for entry-level candidates. "
            "Use the first day of the month for employment dates. "
            "Use a fictional contact address at example.com. "
            "Do not copy the identity or contact details of a real person.\n"
            + reference_instructions()
        ),
    )


def generate_profile(brief: str, *, settings: Settings) -> CandidateProfile:
    """Generate a profile in memory; this function makes paid model requests."""
    if not brief.strip():
        raise ValueError("Candidate brief must not be empty.")
    agent = create_profile_agent(create_text_model(settings))
    result = agent.run_sync(
        f"Today: {date.today().isoformat()}\nCandidate brief:\n{brief}",
        usage_limits=UsageLimits(request_limit=3),
    )
    return result.output
