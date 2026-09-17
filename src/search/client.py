from elasticsearch import Elasticsearch

from settings import Settings


def create_elasticsearch_client(settings: Settings) -> Elasticsearch:
    """Create an Elasticsearch client configured from application settings."""
    return Elasticsearch(settings.elasticsearch_url)


def check_elasticsearch_connection(client: Elasticsearch) -> dict:
    """Return cluster metadata or raise a clear error when Elasticsearch is unavailable."""
    try:
        return client.info()
    except Exception as exc:
        raise RuntimeError(
            "Cannot connect to Elasticsearch. Start it with `docker compose up -d`."
        ) from exc


def search_by_field(
    client: Elasticsearch,
    index_name: str,
    *,
    field: str,
    value: str,
    limit: int = 10,
) -> list[dict]:
    """Search indexed candidates by a structured field value."""
    if not value.strip():
        raise ValueError("Field search value must not be empty.")
    if limit < 1:
        raise ValueError("Search limit must be positive.")

    nested_path = None
    if field.startswith("languages."):
        nested_path = "languages"
    elif field.startswith("experience."):
        nested_path = "experience"
    elif field.startswith("education."):
        nested_path = "education"

    clause = {"match": {field: value.strip()}}
    query = clause
    if nested_path:
        query = {"nested": {"path": nested_path, "query": clause}}

    response = client.search(
        index=index_name,
        query=query,
        size=limit,
        source={"excludes": ["embedding", "full_text"]},
    )
    return _hits_to_results(response)


def search_by_embedding(
    client: Elasticsearch,
    index_name: str,
    embedding: list[float],
    *,
    limit: int = 10,
    min_score: float | None = None,
) -> list[dict]:
    """Search indexed candidates by cosine similarity to an embedding."""
    if not embedding:
        raise ValueError("Semantic search embedding must not be empty.")
    if limit < 1:
        raise ValueError("Search limit must be positive.")
    if min_score is not None and min_score < 0:
        raise ValueError("Minimum score must not be negative.")

    search_options = {
        "index": index_name,
        "knn": {
            "field": "embedding",
            "query_vector": embedding,
            "k": limit,
            "num_candidates": max(limit * 10, 100),
        },
        "size": limit,
        "source": {"excludes": ["embedding", "full_text"]},
    }
    if min_score is not None:
        search_options["min_score"] = min_score
    response = client.search(**search_options)
    return _hits_to_results(response)


def get_candidate_by_name(
    client: Elasticsearch,
    index_name: str,
    *,
    name: str,
) -> dict | None:
    """Retrieve one indexed candidate whose full name matches the supplied name."""
    if not name.strip():
        raise ValueError("Candidate name must not be empty.")
    response = client.search(
        index=index_name,
        query={"match_phrase": {"full_name": name.strip()}},
        size=1,
        source={"excludes": ["embedding", "full_text"]},
    )
    results = _hits_to_results(response)
    return results[0] if results else None


def _hits_to_results(response: dict) -> list[dict]:
    """Convert an Elasticsearch response into compact JSON-serializable results."""
    results = []
    for hit in response.get("hits", {}).get("hits", []):
        result = dict(hit.get("_source", {}))
        result["id"] = hit.get("_id")
        if "_score" in hit:
            result["score"] = hit["_score"]
        results.append(result)
    return results
