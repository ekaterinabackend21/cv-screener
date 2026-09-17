import argparse


def main() -> None:
    """Run CLI commands; profile generation prints data without saving files."""
    parser = argparse.ArgumentParser(prog="cv-screener")
    commands = parser.add_subparsers(dest="command")
    generate = commands.add_parser(
        "generate-profile",
        help="Generate one profile through the configured API and print it; no PDF yet.",
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

    from generation.service import generate_profile
    from settings import Settings

    if not args.brief.strip():
        parser.error("--brief must not be empty.")
    try:
        settings = Settings()
        settings.model_credentials()
    except ValueError:
        parser.error(
            "Check .env: set API_KEY, BASE_URL and LLM_MODEL "
            "(a plain model ID without a provider prefix)."
        )
    profile = generate_profile(args.brief, settings=settings)
    print(profile.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
