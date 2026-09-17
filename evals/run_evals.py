import json
import sys
import unicodedata
from pathlib import Path
from typing import Any

from settings import Settings
from search.client import check_elasticsearch_connection, create_elasticsearch_client
from chat.agent import answer_question


ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = ROOT / "manifest.json"
NO_MATCH_MARKERS = (
    "no matching",
    "no candidate",
    "none of the candidates",
    "couldn't find",
    "could not find",
    "not found",
    "no one",
)


def normalize_text(value: str) -> str:
    """Normalize text for case-insensitive and accent-insensitive name checks."""
    normalized = unicodedata.normalize("NFKD", value)
    without_marks = "".join(char for char in normalized if not unicodedata.combining(char))
    return " ".join(without_marks.casefold().split())


def load_manifest() -> dict[str, Any]:
    """Load the fixed eval cases and expected candidate names from JSON."""
    with MANIFEST_PATH.open(encoding="utf-8") as stream:
        return json.load(stream)


def case_passes(case: dict[str, Any], answer: str) -> bool:
    """Check one agent answer against the expectations declared in the manifest."""
    normalized_answer = normalize_text(answer)
    expected_any = case.get("expected_any", [])
    expected_all = case.get("expected_all", [])
    if expected_any and not any(normalize_text(name) in normalized_answer for name in expected_any):
        return False
    if expected_all and not all(normalize_text(name) in normalized_answer for name in expected_all):
        return False
    if case.get("expected_none"):
        return any(marker in normalized_answer for marker in NO_MATCH_MARKERS)
    return bool(normalized_answer)


def run_case(case: dict[str, Any], *, settings: Settings, client: Any) -> tuple[bool, str]:
    """Run one question through the chat agent and return its pass status and answer."""
    try:
        answer = answer_question(case["question"], settings=settings, client=client)
    except Exception as exc:
        return False, f"error: {exc}"
    return case_passes(case, answer), answer


def main() -> int:
    """Run all fixed chat evaluations and print a pass/fail summary."""
    manifest = load_manifest()
    settings = Settings()
    settings.model_credentials()
    client = create_elasticsearch_client(settings)
    check_elasticsearch_connection(client)
    if not client.indices.exists(index=settings.elasticsearch_index):
        print(
            f"Index '{settings.elasticsearch_index}' does not exist. "
            "Ingest evals/fixtures into this index first.",
            file=sys.stderr,
        )
        return 1

    passed = 0
    for case in manifest["cases"]:
        ok, answer = run_case(case, settings=settings, client=client)
        label = "PASS" if ok else "FAIL"
        print(f"[{label}] {case['id']}")
        print(f"  Question: {case['question']}")
        print(f"  Answer: {answer}")
        if ok:
            passed += 1

    total = len(manifest["cases"])
    print(f"\nPassed: {passed}/{total}")
    print(f"Overall: {'PASS' if passed == total else 'FAIL'}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
