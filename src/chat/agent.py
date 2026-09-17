import json
from dataclasses import dataclass
from typing import Any

from elasticsearch import Elasticsearch
from pydantic_ai import Agent, RunContext
from pydantic_ai.models import Model
from pydantic_ai.usage import UsageLimits

from indexing.embeddings import embed_text
from llm import create_text_model
from search.client import (
    get_candidate_by_name,
    search_by_embedding,
    search_by_field,
)
from settings import Settings


FIELD_SEARCH_OPTIONS = (
    "first_name",
    "last_name",
    "position",
    "seniority",
    "location",
    "skills",
    "languages.name",
    "languages.level",
    "experience.company",
    "experience.technologies",
    "education.institution",
)


@dataclass(frozen=True)
class ChatDependencies:
    """Runtime dependencies shared by the chat agent and its search tools."""

    settings: Settings
    client: Elasticsearch


def _compact_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    """Keep tool output focused on facts useful for answering candidate questions."""
    fields = (
        "id",
        "full_name",
        "first_name",
        "last_name",
        "position",
        "seniority",
        "location",
        "summary",
        "skills",
        "languages",
        "experience",
        "education",
        "score",
    )
    return {field: candidate[field] for field in fields if field in candidate}


def _format_tool_results(results: list[dict[str, Any]]) -> str:
    """Serialize search results into explicit JSON for the model context."""
    return json.dumps(
        [_compact_candidate(result) for result in results],
        ensure_ascii=False,
    )


def create_chat_agent(model: Model) -> Agent[ChatDependencies, str]:
    """Build the chat agent that answers only from Elasticsearch tool results."""
    agent = Agent[ChatDependencies, str](
        model,
        deps_type=ChatDependencies,
        output_type=str,
        retries=2,
        instructions=(
            "You answer questions about the indexed CV dataset. "
            "You must use one or more search tools before making any factual claim "
            "about a candidate. Never invent a candidate, skill, language, role, "
            "company, date or achievement. Use get_candidate_profile for a named "
            "candidate and semantic or field search for discovery questions. "
            "Only use facts present in tool results. Name the matching candidates "
            "in every answer. If tools return no candidates, clearly say that no "
            "matching candidate was found. For best-fit questions, explain the "
            "choice using retrieved evidence and mention relevant limitations."
        ),
    )

    @agent.tool
    def search_candidates_by_field(
        ctx: RunContext[ChatDependencies],
        field: str,
        value: str,
        limit: int = 5,
    ) -> str:
        """Find candidates whose structured field matches the requested value."""
        if field not in FIELD_SEARCH_OPTIONS:
            return json.dumps({"error": f"Unsupported field. Use one of: {FIELD_SEARCH_OPTIONS}"})
        try:
            results = search_by_field(
                ctx.deps.client,
                ctx.deps.settings.elasticsearch_index,
                field=field,
                value=value,
                limit=min(max(limit, 1), 10),
            )
        except ValueError as exc:
            return json.dumps({"error": str(exc)})
        return _format_tool_results(results)

    @agent.tool
    def search_candidates_semantically(
        ctx: RunContext[ChatDependencies],
        query: str,
        limit: int = 5,
        min_score: float | None = 0.7,
    ) -> str:
        """Find candidates by semantic similarity using the local embedding model."""
        try:
            embedding = embed_text(query, settings=ctx.deps.settings)
            results = search_by_embedding(
                ctx.deps.client,
                ctx.deps.settings.elasticsearch_index,
                embedding,
                limit=min(max(limit, 1), 10),
                min_score=min_score,
            )
        except ValueError as exc:
            return json.dumps({"error": str(exc)})
        return _format_tool_results(results)

    @agent.tool
    def get_candidate_profile(
        ctx: RunContext[ChatDependencies],
        name: str,
    ) -> str:
        """Retrieve the indexed profile for one candidate by full name."""
        try:
            candidate = get_candidate_by_name(
                ctx.deps.client,
                ctx.deps.settings.elasticsearch_index,
                name=name,
            )
        except ValueError as exc:
            return json.dumps({"error": str(exc)})
        if candidate is None:
            return "[]"
        return _format_tool_results([candidate])

    return agent


def answer_question(
    question: str,
    *,
    settings: Settings,
    client: Elasticsearch,
) -> str:
    """Run one user question through the tool-using chat agent."""
    if not question.strip():
        raise ValueError("Chat question must not be empty.")
    agent = create_chat_agent(create_text_model(settings))
    result = agent.run_sync(
        question,
        deps=ChatDependencies(settings=settings, client=client),
        usage_limits=UsageLimits(request_limit=6),
    )
    return result.output
