from pathlib import Path

from settings import Settings
from search.client import check_elasticsearch_connection, create_elasticsearch_client
from indexing.embeddings import embed_text
from indexing.extractor import extract_profile
from indexing.pdf_reader import collect_pdf_files, file_sha256, read_pdf_text
from indexing.repository import index_profile


def ingest_path(input_path: Path, *, settings: Settings) -> int:
    """Parse, embed, and index every PDF under a file or directory path."""
    files = collect_pdf_files(input_path)
    if not files:
        raise ValueError(f"No PDF files found at: {input_path}")
    client = create_elasticsearch_client(settings)
    check_elasticsearch_connection(client)
    if not client.indices.exists(index=settings.elasticsearch_index):
        raise RuntimeError(
            f"Index '{settings.elasticsearch_index}' does not exist. "
            "Run `docker compose up -d` first."
        )
    for position, path in enumerate(files, start=1):
        print(f"[{position}/{len(files)}] Reading {path.name}...")
        full_text = read_pdf_text(path)
        file_hash = file_sha256(path)
        print(f"[{position}/{len(files)}] Extracting structured fields...")
        profile = extract_profile(full_text, settings=settings)
        print(f"[{position}/{len(files)}] Computing local embedding...")
        embedding = embed_text(full_text, settings=settings)
        index_profile(
            client,
            settings.elasticsearch_index,
            profile,
            full_text=full_text,
            embedding=embedding,
            source_file=path,
            file_hash=file_hash,
        )
        print(f"[{position}/{len(files)}] Indexed {profile.first_name} {profile.last_name}.")
    return len(files)
