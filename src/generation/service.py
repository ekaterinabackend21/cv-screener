from datetime import date

from pydantic_ai import Agent
from pydantic_ai.models import Model
from pydantic_ai.usage import UsageLimits

from generation.models import CandidateProfile
from llm import create_text_model
from settings import Settings


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
            "Do not copy the identity or contact details of a real person."
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
