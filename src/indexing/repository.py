from pathlib import Path

from elasticsearch import Elasticsearch

from generation.models import CandidateProfile


def index_profile(
    client: Elasticsearch,
    index_name: str,
    profile: CandidateProfile,
    *,
    full_text: str,
    embedding: list[float],
    source_file: Path,
    file_hash: str,
) -> str:
    """Upsert one parsed CV and its embedding into Elasticsearch."""
    document = profile.model_dump(mode="json")
    document.update(
        {
            "full_name": f"{profile.first_name} {profile.last_name}",
            "full_text": full_text,
            "embedding": embedding,
            "source_file": str(source_file),
            "file_hash": file_hash,
        }
    )
    client.index(index=index_name, id=file_hash, document=document, refresh="wait_for")
    return file_hash
