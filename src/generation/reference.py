from importlib.resources import files
from io import BytesIO

from pypdf import PdfReader


def read_reference() -> PdfReader:
    """Load the bundled example PDF independently of the working directory."""
    resource = files("generation").joinpath("resources/cv-example.pdf")
    return PdfReader(BytesIO(resource.read_bytes()))


def reference_instructions() -> str:
    """Describe the reference layout and supply its body as a writing example."""
    text = "\n".join(page.extract_text() or "" for page in read_reference().pages)
    marker = "PROFILE"
    if marker not in text:
        raise ValueError("The reference CV must contain a PROFILE section.")
    body = text[text.index(marker):]
    return (
        "Use the following reference CV body only as an example of structure, "
        "specificity and concise writing. Do not copy its companies, achievements, "
        "education or biography. Its identifying header and photograph are omitted. "
        "The PDF service uses its layout: portrait at the upper left, name and role "
        "beside it, warm gray section rules, PROFILE, CORE SKILLS, EXPERIENCE and "
        "EDUCATION. Also supply languages, which our template adds. "
        "Aim for 350-450 words overall, with a 40-60 word summary, 2-3 concise "
        "bullets for recent jobs and 1-2 for earlier jobs. The result must fit one A4 page.\n"
        "<reference_cv>\n" + body + "\n</reference_cv>"
    )
