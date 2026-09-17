import argparse
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
    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        return

    from generation.service import generate_candidate_briefs, generate_profile
    from settings import Settings

    try:
        settings = Settings()
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
