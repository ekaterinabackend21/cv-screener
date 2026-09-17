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
