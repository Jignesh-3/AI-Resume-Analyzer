import io
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

def generate_ats_pdf(data: dict) -> io.BytesIO:
    """
    Generates a single-column, ATS-parseable PDF in-memory.
    Ensures linear reading order and UTF-8 encoding compatibility.
    """
    buffer = io.BytesIO()
    
    # 0.5 inch margins (36 points) maximize printable area for ATS scanners
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    
    # Custom ATS-compliant typography styles (Helvetica is universally standard)
    name_style = ParagraphStyle(
        'ATS_Name',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#111827")
    )
    
    contact_style = ParagraphStyle(
        'ATS_Contact',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#4B5563")
    )
    
    section_heading = ParagraphStyle(
        'ATS_SectionHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#111827"),
        spaceBefore=10,
        spaceAfter=3
    )
    
    role_title = ParagraphStyle(
        'ATS_RoleTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#1F2937")
    )
    
    bullet_style = ParagraphStyle(
        'ATS_Bullet',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13,
        leftIndent=12,
        firstLineIndent=-8,
        textColor=colors.HexColor("#374151"),
        spaceAfter=3
    )
    
    body_text = ParagraphStyle(
        'ATS_Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#374151")
    )

    story = []
    
    # --- 1. HEADER SECTION ---
    candidate_name = data.get("candidate_name", "CANDIDATE NAME").upper()
    story.append(Paragraph(candidate_name, name_style))
    story.append(Spacer(1, 4))
    
    contact_items = []
    for field in ["email", "phone", "location", "linkedin", "github"]:
        val = data.get(field)
        if val:
            contact_items.append(val)
            
    contact_line = " | ".join(contact_items) if contact_items else "contact@example.com | Portfolio"
    story.append(Paragraph(contact_line, contact_style))
    story.append(Spacer(1, 8))
    
    def add_section_divider(title: str):
        story.append(Paragraph(title.upper(), section_heading))
        story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#9CA3AF"), spaceBefore=2, spaceAfter=6))

    # --- 2. PROFESSIONAL EXPERIENCE ---
    experiences = data.get("experiences", [])
    if experiences:
        add_section_divider("Professional Experience")
        for exp in experiences:
            company = exp.get("company", "Company")
            role = exp.get("role", "Software Engineer")
            duration = exp.get("duration", "")
            location = exp.get("location", "")
            
            # Format header: Role | Company (Location, Duration)
            meta = f" — {location}" if location else ""
            dur_str = f" | {duration}" if duration else ""
            header_text = f"<b>{role}</b>, {company}{meta}{dur_str}"
            story.append(Paragraph(header_text, role_title))
            story.append(Spacer(1, 2))
            
            # Bullets (using the rewritten Google XYZ bullet points)
            for bullet in exp.get("bullets", []):
                story.append(Paragraph(f"• {bullet}", bullet_style))
            story.append(Spacer(1, 6))

    # --- 3. TECHNICAL SKILLS ---
    skills = data.get("skills", {})
    if skills:
        add_section_divider("Technical Skills")
        if isinstance(skills, dict):
            for category, items in skills.items():
                items_str = ", ".join(items) if isinstance(items, list) else str(items)
                story.append(Paragraph(f"<b>{category}:</b> {items_str}", body_text))
                story.append(Spacer(1, 2))
        elif isinstance(skills, list):
            story.append(Paragraph(", ".join(skills), body_text))
        story.append(Spacer(1, 6))

    # --- 4. EDUCATION ---
    education = data.get("education", [])
    if education:
        add_section_divider("Education")
        for edu in education:
            degree = edu.get("degree", "Degree")
            institution = edu.get("institution", "University")
            year = edu.get("year", "")
            details = f"<b>{degree}</b> — {institution} ({year})" if year else f"<b>{degree}</b> — {institution}"
            story.append(Paragraph(details, body_text))
            story.append(Spacer(1, 3))

    # Build the PDF flowable document into our in-memory buffer
    doc.build(story)
    buffer.seek(0)
    return buffer