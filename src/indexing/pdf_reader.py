import hashlib
from pathlib import Path

from pypdf import PdfReader


def read_pdf_text(path: Path) -> str:
    """Extract the text layer from every page of a PDF file."""
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a PDF file, got: {path}")
    reader = PdfReader(path)
    text = "\n\n".join(page.extract_text() or "" for page in reader.pages).strip()
    if not text:
        raise ValueError(f"No text layer found in PDF: {path}")
    return text


def file_sha256(path: Path) -> str:
    """Return the SHA-256 digest of a file for idempotent indexing."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect_pdf_files(input_path: Path) -> list[Path]:
    """Collect PDF files from one path in deterministic order."""
    if input_path.is_file():
        return [input_path] if input_path.suffix.lower() == ".pdf" else []
    if input_path.is_dir():
        return sorted(path for path in input_path.glob("*.pdf") if path.is_file())
    raise FileNotFoundError(f"Input path does not exist: {input_path}")
