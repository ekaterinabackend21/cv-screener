import argparse
import json
from pathlib import Path
import re
from datetime import datetime


def main() -> None:
    """Run the profile inspection and complete PDF generation CLI commands."""
    parser = argparse.ArgumentParser(prog="cv-screener")
    commands = parser.add_subparsers(dest="command")
    generate_batch = commands.add_parser(
        "generate",
        help="Generate profiles, synthetic portraits and one-page PDF resumes.",
    )
    generate_batch.add_argument(
        "--count", type=int, choices=(1, 3, 5, 10), default=10,
        help="Number of distinct resumes to generate (default: 10).",
    )
    generate_batch.add_argument(
        "--with-images", action="store_true",
        help="Call the image API for portraits; requires IMAGE_GENERATION_ENABLED=true.",
    )
    generate = commands.add_parser(
        "generate-profile",
        help="Generate one profile and print its structured data.",
    )
    generate.add_argument(
        "--brief",
        required=True,
        help="Describe the fictional candidate's role, seniority and background.",
    )
    ingest = commands.add_parser(
        "ingest",
        help="Parse PDF resumes and index their fields and embeddings.",
    )
    ingest.add_argument("--input", type=Path, required=True, help="PDF file or directory of PDFs.")
    search = commands.add_parser(
        "search",
        help="Search indexed resumes by a field or by semantic similarity.",
    )
    search.add_argument(
        "--mode", choices=("field", "semantic"), required=True,
        help="Search mode: structured field matching or semantic similarity.",
    )
    search.add_argument(
        "--field",
        help="Structured field, for example skills, seniority or languages.name.",
    )
    search.add_argument("--value", help="Value for a structured field search.")
    search.add_argument("--query", help="Natural-language query for semantic search.")
    search.add_argument(
        "--limit", type=int, default=10,
        help="Maximum number of results (default: 10).",
    )
    search.add_argument(
        "--min-score", type=float,
        help="Minimum Elasticsearch score for semantic results.",
    )
    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        return

    from generation.service import generate_candidate_briefs, generate_profile
    from settings import Settings

    try:
        settings = Settings()
        if args.command in {"generate", "generate-profile", "ingest"}:
            settings.model_credentials()
    except ValueError:
        parser.error(
            "Check .env: set API_KEY, BASE_URL and LLM_MODEL "
            "(a plain model ID without a provider prefix)."
        )
    if args.command == "generate-profile":
        if not args.brief.strip():
            parser.error("--brief must not be empty.")
        profile = generate_profile(args.brief, settings=settings)
        print(profile.model_dump_json(indent=2))
        return

    if args.command == "ingest":
        from indexing.pipeline import ingest_path

        try:
            count = ingest_path(args.input, settings=settings)
        except (FileNotFoundError, RuntimeError, ValueError) as exc:
            parser.error(str(exc))
        print(f"Indexed {count} PDF file(s) into {settings.elasticsearch_index}.")
        return

    if args.command == "search":
        if args.limit < 1:
            parser.error("--limit must be positive.")
        if args.min_score is not None and args.min_score < 0:
            parser.error("--min-score must not be negative.")
        if args.mode == "field" and (not args.field or not args.value):
            parser.error("Field search requires both --field and --value.")
        if args.mode == "semantic" and not args.query:
            parser.error("Semantic search requires --query.")
        from search.client import (
            check_elasticsearch_connection,
            create_elasticsearch_client,
            search_by_embedding,
            search_by_field,
        )

        try:
            client = create_elasticsearch_client(settings)
            check_elasticsearch_connection(client)
            if not client.indices.exists(index=settings.elasticsearch_index):
                raise RuntimeError(
                    f"Index '{settings.elasticsearch_index}' does not exist. "
                    "Run `docker compose up -d` first."
                )
            if args.mode == "field":
                results = search_by_field(
                    client,
                    settings.elasticsearch_index,
                    field=args.field,
                    value=args.value,
                    limit=args.limit,
                )
            else:
                from indexing.embeddings import embed_text

                results = search_by_embedding(
                    client,
                    settings.elasticsearch_index,
                    embed_text(args.query, settings=settings),
                    limit=args.limit,
                    min_score=args.min_score,
                )
        except (RuntimeError, ValueError) as exc:
            parser.error(str(exc))
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return

    from generation.pdf import render_resume

    if args.with_images and not settings.image_generation_enabled:
        parser.error(
            "Image generation is disabled by IMAGE_GENERATION_ENABLED=false. "
            "Set it to true before using --with-images."
        )
    generate_portrait = None
    if args.with_images:
        from generation.image import generate_portrait

    output_root = Path(settings.output_dir)
    timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M")
    batch_dir = output_root / f"cv-{timestamp}"
    suffix = 2
    while batch_dir.exists():
        batch_dir = output_root / f"cv-{timestamp}_{suffix:02d}"
        suffix += 1
    batch_dir.mkdir(parents=True, exist_ok=False)
    print(f"Planning {args.count} varied candidate briefs...")
    briefs = generate_candidate_briefs(args.count, settings=settings)
    for index, brief in enumerate(briefs, start=1):
        print(f"[{index}/{args.count}] Generating profile...")
        profile = generate_profile(brief, settings=settings)
        portrait = None
        if generate_portrait is not None:
            print(f"[{index}/{args.count}] Generating synthetic portrait...")
            portrait = generate_portrait(profile, settings=settings)
        else:
            print(f"[{index}/{args.count}] Image generation disabled; using empty photo slot.")
        pdf = render_resume(profile, portrait)
        filename = re.sub(
            r"[^a-z0-9]+", "_",
            f"{profile.first_name}_{profile.last_name}_{profile.position}".lower(),
        ).strip("_") + ".pdf"
        (batch_dir / filename).write_bytes(pdf)
        print(f"[{index}/{args.count}] Saved {batch_dir / filename}")
    print(f"Generated {args.count} resumes in {batch_dir}")


if __name__ == "__main__":
    main()
