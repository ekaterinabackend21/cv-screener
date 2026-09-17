from datetime import date
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

import reportlab
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Paragraph, Spacer

from generation.models import CandidateProfile
from generation.reference import read_reference


ACCENT = colors.HexColor("#70665C")
RULE = colors.HexColor("#C8C1B9")
INK = colors.HexColor("#292724")
MARGIN = 42


def register_fonts() -> None:
    """Register bundled Unicode fonts and bold/italic variants for PDF paragraphs."""
    directory = Path(reportlab.__file__).parent / "fonts"
    for name, filename in (
        ("CV", "Vera.ttf"),
        ("CV-Bold", "VeraBd.ttf"),
        ("CV-Italic", "VeraIt.ttf"),
        ("CV-BoldItalic", "VeraBI.ttf"),
    ):
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, str(directory / filename)))
    pdfmetrics.registerFontFamily(
        "CV", normal="CV", bold="CV-Bold", italic="CV-Italic", boldItalic="CV-BoldItalic"
    )


def month_label(value: date | None) -> str:
    """Format an employment month or label an ongoing position."""
    return value.strftime("%m/%Y") if value else "Present"


def body_blocks(profile: CandidateProfile, font_size: float) -> list:
    """Build reference-inspired sections with all profile content and escaped text."""
    body = ParagraphStyle(
        "body", fontName="CV", fontSize=font_size,
        leading=font_size * 1.35, textColor=INK, spaceAfter=3,
    )
    heading = ParagraphStyle(
        "heading", parent=body, textColor=ACCENT, fontSize=11,
        leading=15, alignment=1, spaceBefore=9, spaceAfter=5,
    )
    small = ParagraphStyle(
        "small", parent=body, fontSize=font_size - 0.5,
        leading=font_size * 1.25, textColor=ACCENT,
    )
    bullet = ParagraphStyle("bullet", parent=body, leftIndent=10, firstLineIndent=-8)
    blocks = [Paragraph("PROFILE", heading), Paragraph(escape(profile.summary), body)]
    blocks += [Paragraph("CORE SKILLS", heading), Paragraph(escape(" · ".join(profile.skills)), body)]
    blocks.append(Paragraph("EXPERIENCE", heading))
    for job in profile.experience:
        blocks.append(Paragraph(
            f"<b>{escape(job.company)}</b> | {escape(job.position)}"
            f"<br/><font color='#70665C'>{month_label(job.start_date)} - "
            f"{month_label(job.end_date)}</font>", body,
        ))
        blocks.extend(Paragraph("• " + escape(item), bullet) for item in job.achievements)
        blocks.append(Paragraph("Tech: " + escape(", ".join(job.technologies)), small))
        blocks.append(Spacer(1, 4))
    blocks.append(Paragraph("EDUCATION", heading))
    for item in profile.education:
        blocks.append(Paragraph(
            f"<b>{escape(item.institution)}</b><br/>"
            f"{escape(item.qualification)}, {escape(item.field_of_study)}"
            f" · {item.start_year}-{item.end_year or 'Present'}", body,
        ))
    blocks += [Paragraph("LANGUAGES", heading), Paragraph(escape(" · ".join(
        f"{item.name}: {item.level}" for item in profile.languages
    )), body)]
    return blocks


def draw_header(canvas: Canvas, profile: CandidateProfile, portrait: bytes | None,
                width: float, height: float) -> float:
    """Draw a circular upper-left portrait and wrapped identity and contact text."""
    top = height - MARGIN
    diameter = 68
    if portrait:
        image = ImageReader(BytesIO(portrait))
        iw, ih = image.getSize()
        scale = diameter / min(iw, ih)
        canvas.saveState()
        circle = canvas.beginPath()
        circle.circle(MARGIN + diameter / 2, top - diameter / 2, diameter / 2)
        canvas.clipPath(circle, stroke=0)
        canvas.drawImage(
            image, MARGIN + (diameter - iw * scale) / 2,
            top - diameter + (diameter - ih * scale) / 2,
            width=iw * scale, height=ih * scale, mask="auto",
        )
        canvas.restoreState()
    else:
        canvas.setFillColor(colors.HexColor("#F0EDE9"))
        canvas.circle(MARGIN + diameter / 2, top - diameter / 2, diameter / 2, stroke=0, fill=1)
        canvas.setFillColor(ACCENT)
        canvas.setFont("CV", 8)
        canvas.drawCentredString(MARGIN + diameter / 2, top - diameter / 2, "PHOTO")
    x = MARGIN + diameter + 16
    available = width - MARGIN - x
    y = top
    for content, size, bold in (
        (f"{profile.first_name} {profile.last_name}".upper(), 20, True),
        (profile.position, 11, True),
        (f"{profile.seniority.title()} · {profile.location}", 9, False),
        (profile.email, 9, False),
    ):
        paragraph = Paragraph(escape(content), ParagraphStyle(
            "header", fontName="CV-Bold" if bold else "CV",
            fontSize=size, leading=size * 1.3, textColor=ACCENT if size == 20 else INK,
        ))
        _, block_height = paragraph.wrap(available, height)
        y -= block_height
        paragraph.drawOn(canvas, x, y)
        y -= 3
    bottom = min(top - diameter, y) - 10
    canvas.setStrokeColor(RULE)
    canvas.line(MARGIN, bottom, width - MARGIN, bottom)
    return bottom - 3


def render_resume(profile: CandidateProfile, portrait: bytes | None, *,
                  preview: bool = False) -> bytes:
    """Render one page in memory, using an empty photo slot when no portrait exists."""
    register_fonts()
    reference_page = read_reference().pages[0]
    width, height = float(reference_page.mediabox.width), float(reference_page.mediabox.height)
    for font_size in (10, 9.5, 9):
        buffer = BytesIO()
        canvas = Canvas(buffer, pagesize=(width, height))
        canvas.setTitle(f"{profile.first_name} {profile.last_name} - {profile.position}")
        y = draw_header(canvas, profile, portrait, width, height)
        blocks = body_blocks(profile, font_size)
        measured = [(block, block.wrap(width - 2 * MARGIN, height)[1]) for block in blocks]
        required = sum(h + b.getSpaceBefore() + b.getSpaceAfter() for b, h in measured)
        if required > y - MARGIN:
            continue
        for block, block_height in measured:
            y -= block.getSpaceBefore() + block_height
            if isinstance(block, Paragraph) and block.style.name == "heading":
                label_width = pdfmetrics.stringWidth(block.getPlainText(), "CV", 11)
                midpoint = width / 2
                line_y = y + block_height / 2
                canvas.setStrokeColor(RULE)
                canvas.line(MARGIN, line_y, midpoint - label_width / 2 - 10, line_y)
                canvas.line(midpoint + label_width / 2 + 10, line_y, width - MARGIN, line_y)
            block.drawOn(canvas, MARGIN, y)
            y -= block.getSpaceAfter()
        canvas.showPage()
        canvas.save()
        data = buffer.getvalue()
        if len(PdfReader(BytesIO(data)).pages) != 1:
            raise ValueError("The resume must contain exactly one page.")
        return data
    raise ValueError("The profile is too long for one readable page; shorten it before rendering.")
