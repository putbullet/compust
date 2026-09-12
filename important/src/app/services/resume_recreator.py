import io
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from docx import Document
from docx.shared import Pt, Inches, RGBColor
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from pypdf import PdfReader
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from ..models import CustomizedResume, Job, Resume
from .resume_customization import analyze_resume_alignment


STORAGE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "storage" / "customized_resumes"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


class ResumeValidationError(Exception):
    pass


def validate_generated_resume_pdf(pdf_path: Path) -> None:
    """Validate that the generated PDF opens cleanly, contains extractable text, and has reasonable pages."""
    if not pdf_path.exists() or pdf_path.stat().st_size < 100:
        raise ResumeValidationError("Generated PDF file is empty or missing.")

    try:
        reader = PdfReader(str(pdf_path))
    except Exception as exc:
        raise ResumeValidationError(f"Generated PDF cannot be opened: {exc}")

    if len(reader.pages) == 0:
        raise ResumeValidationError("Generated PDF contains 0 pages.")

    if len(reader.pages) > 4:
        raise ResumeValidationError(f"Generated PDF exceeded reasonable page count ({len(reader.pages)} pages).")

    total_text = ""
    for page in reader.pages:
        txt = page.extract_text() or ""
        total_text += txt

    if len(total_text.strip()) < 30:
        raise ResumeValidationError("Generated PDF does not contain extractable text layer.")


def render_pdf_resume(
    dest_path: Path,
    user_name: str,
    sections: dict[str, Any],
    job: Job,
) -> None:
    """Render a clean, professional ATS-friendly PDF resume using ReportLab Platypus."""
    doc = SimpleDocTemplate(
        str(dest_path),
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    header_style = ParagraphStyle(
        "HeaderName",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0f172a"),
        alignment=0,
    )
    subhead_style = ParagraphStyle(
        "SubHead",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#475569"),
    )
    section_title_style = ParagraphStyle(
        "SecTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#1e3a8a"),
        spaceBefore=10,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor("#1e293b"),
    )
    bullet_style = ParagraphStyle(
        "Bullet",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#1e293b"),
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=2,
    )

    story = []

    # Header / Name
    story.append(Paragraph(user_name or "Curriculum Vitae", header_style))
    story.append(Paragraph(f"Tailored for: {job.title} | COMPUST Professional Intelligence", subhead_style))
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1"), spaceBefore=2, spaceAfter=8))

    # Summary
    if sections.get("summary"):
        story.append(Paragraph("PROFESSIONAL SUMMARY", section_title_style))
        story.append(Paragraph(sections["summary"].replace("\n", "<br/>"), body_style))
        story.append(Spacer(1, 6))

    # Skills
    if sections.get("skills"):
        story.append(Paragraph("TECHNICAL & CORE SKILLS", section_title_style))
        skills_text = ", ".join(sections["skills"]) if isinstance(sections["skills"], list) else str(sections["skills"])
        story.append(Paragraph(skills_text, body_style))
        story.append(Spacer(1, 6))

    # Experience
    if sections.get("experience"):
        story.append(Paragraph("PROFESSIONAL EXPERIENCE", section_title_style))
        exp_lines = [l.strip() for l in str(sections["experience"]).splitlines() if l.strip()]
        for line in exp_lines:
            if line.startswith(("-", "•", "*", "·")):
                story.append(Paragraph(f"• {line.lstrip('-•*· ')}", bullet_style))
            else:
                story.append(Paragraph(line, body_style))
        story.append(Spacer(1, 6))

    # Education
    if sections.get("education"):
        story.append(Paragraph("EDUCATION & ACADEMIC BACKGROUND", section_title_style))
        edu_lines = [l.strip() for l in str(sections["education"]).splitlines() if l.strip()]
        for line in edu_lines:
            story.append(Paragraph(line, body_style))
        story.append(Spacer(1, 6))

    # Projects
    if sections.get("projects"):
        story.append(Paragraph("PROJECTS", section_title_style))
        proj_lines = [l.strip() for l in str(sections["projects"]).splitlines() if l.strip()]
        for line in proj_lines:
            story.append(Paragraph(line, body_style))
        story.append(Spacer(1, 6))

    # Certifications
    if sections.get("certifications"):
        story.append(Paragraph("CERTIFICATIONS", section_title_style))
        cert_lines = [l.strip() for l in str(sections["certifications"]).splitlines() if l.strip()]
        for line in cert_lines:
            story.append(Paragraph(line, body_style))
        story.append(Spacer(1, 6))

    # Languages
    if sections.get("languages"):
        story.append(Paragraph("LANGUAGES", section_title_style))
        langs_text = ", ".join(sections["languages"]) if isinstance(sections["languages"], list) else str(sections["languages"])
        story.append(Paragraph(langs_text, body_style))

    doc.build(story)


def render_docx_resume(
    dest_path: Path,
    user_name: str,
    sections: dict[str, Any],
    job: Job,
) -> None:
    """Render an editable ATS-friendly DOCX document."""
    doc = Document()

    # Document Margins
    sections_doc = doc.sections
    for s in sections_doc:
        s.top_margin = Inches(0.6)
        s.bottom_margin = Inches(0.6)
        s.left_margin = Inches(0.6)
        s.right_margin = Inches(0.6)

    # Name Header
    h1 = doc.add_heading(user_name or "Curriculum Vitae", level=0)
    h1.runs[0].font.size = Pt(20)
    h1.runs[0].font.color.rgb = RGBColor(15, 23, 42)

    p_sub = doc.add_paragraph()
    p_sub.add_run(f"Tailored for: {job.title} | COMPUST Professional Intelligence").italic = True

    # Summary
    if sections.get("summary"):
        doc.add_heading("PROFESSIONAL SUMMARY", level=1)
        doc.add_paragraph(sections["summary"])

    # Skills
    if sections.get("skills"):
        doc.add_heading("TECHNICAL & CORE SKILLS", level=1)
        skills_text = ", ".join(sections["skills"]) if isinstance(sections["skills"], list) else str(sections["skills"])
        doc.add_paragraph(skills_text)

    # Experience
    if sections.get("experience"):
        doc.add_heading("PROFESSIONAL EXPERIENCE", level=1)
        exp_lines = [l.strip() for l in str(sections["experience"]).splitlines() if l.strip()]
        for line in exp_lines:
            if line.startswith(("-", "•", "*", "·")):
                doc.add_paragraph(line.lstrip('-•*· '), style='List Bullet')
            else:
                doc.add_paragraph(line)

    # Education
    if sections.get("education"):
        doc.add_heading("EDUCATION & ACADEMIC BACKGROUND", level=1)
        for line in [l.strip() for l in str(sections["education"]).splitlines() if l.strip()]:
            doc.add_paragraph(line)

    # Projects
    if sections.get("projects"):
        doc.add_heading("PROJECTS", level=1)
        for line in [l.strip() for l in str(sections["projects"]).splitlines() if l.strip()]:
            doc.add_paragraph(line)

    # Certifications
    if sections.get("certifications"):
        doc.add_heading("CERTIFICATIONS", level=1)
        for line in [l.strip() for l in str(sections["certifications"]).splitlines() if l.strip()]:
            doc.add_paragraph(line)

    # Languages
    if sections.get("languages"):
        doc.add_heading("LANGUAGES", level=1)
        langs_text = ", ".join(sections["languages"]) if isinstance(sections["languages"], list) else str(sections["languages"])
        doc.add_paragraph(langs_text)

    doc.save(str(dest_path))


def recreate_customized_resume_for_job(
    db: Session,
    user_id: int,
    base_resume: Resume,
    job: Job,
    user_name: str = "Candidate Profile",
) -> CustomizedResume:
    """
    Generate, validate, and persist a job-specific customized resume version.
    Preserves original base resume, extracts and formats sections, generates PDF + DOCX,
    and runs visual/structural validation before returning.
    """
    # 1. Analyze alignment and recommendations
    skills = [s.strip() for s in (job.description or "").split() if False]
    analysis = analyze_resume_alignment(job, [], base_resume)

    # 2. Determine next version number for this user + job
    existing_count = db.scalar(
        select(CustomizedResume.id)
        .where(CustomizedResume.user_id == user_id, CustomizedResume.job_id == job.id)
    )
    version = 1 if not existing_count else 2

    # 3. Prepare structured sections
    sections = base_resume.parsed_sections or {}

    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    pdf_fname = f"resume_{user_id}_job_{job.id}_v{version}_{timestamp_str}.pdf"
    docx_fname = f"resume_{user_id}_job_{job.id}_v{version}_{timestamp_str}.docx"

    pdf_dest = STORAGE_DIR / pdf_fname
    docx_dest = STORAGE_DIR / docx_fname

    # 4. Render files
    render_pdf_resume(pdf_dest, user_name, sections, job)
    render_docx_resume(docx_dest, user_name, sections, job)

    # 5. Validate generated PDF
    validate_generated_resume_pdf(pdf_dest)

    # 6. Persist record in database
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    custom_record = CustomizedResume(
        user_id=user_id,
        base_resume_id=base_resume.id,
        job_id=job.id,
        version=version,
        pdf_filename=pdf_fname,
        docx_filename=docx_fname,
        raw_text=base_resume.raw_text,
        parsed_sections=sections,
        ats_analysis={
            "already_demonstrated": analysis["already_demonstrated"],
            "missing_or_weak": analysis["missing_or_weak"],
            "ats_improvements": analysis["ats_improvements"],
        },
        recommendations=analysis["actionable_recommendations"],
        created_at=now,
    )

    db.add(custom_record)
    db.commit()
    db.refresh(custom_record)
    return custom_record


def get_customized_resume_file_path(filename: str) -> Path | None:
    p = STORAGE_DIR / filename
    if p.exists() and p.is_file():
        return p
    return None
