import io
import re
from typing import List, Tuple
import pdfplumber


def extract_resume_data(file_bytes: bytes) -> Tuple[str, List[str]]:
    """
    Extracts text from PDF bytes and isolates actionable project/experience bullet points.

    Returns:
        Tuple[str, List[str]]: (full_text, list_of_cleaned_bullets)
    """
    full_text_chunks = []

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text(layout=False) or ""
            if page_text.strip():
                full_text_chunks.append(page_text.strip())

    full_text = "\n\n".join(full_text_chunks)

    if not full_text.strip():
        return "", []

    # Extract distinct bullet points
    bullets = _extract_bullets(full_text)
    return full_text, bullets


def _extract_bullets(text: str) -> List[str]:
    """
    Splits resume text into individual bullet strings using standard bullet markers,
    dashes, or line structure.
    """
    bullet_pattern = re.compile(
        r"(?:^|\n)\s*(?:[•\u2022\u2023\u25E6\u2043\u2219\*\-–—]|(?:\d+\.))\s*(.+?)(?=(?:\n\s*(?:[•\u2022\u2023\u25E6\u2043\u2219\*\-–—]|(?:\d+\.)))|\n\s*\n|$)",
        re.DOTALL
    )

    matches = bullet_pattern.findall(text)
    cleaned_bullets = []

    for item in matches:
        # Collapse whitespace/newlines into a single clean line
        line = re.sub(r"\s+", " ", item).strip()
        if len(line) >= 25 and not _is_likely_header(line):
            cleaned_bullets.append(line)

    # Fallback: if resume has no bullet symbols, take non-header sentences
    if not cleaned_bullets:
        raw_lines = [re.sub(r"\s+", " ", l).strip() for l in text.split("\n")]
        cleaned_bullets = [
            l for l in raw_lines
            if len(l) >= 35 and not _is_likely_header(l)
        ]

    # Limit to top 10 substantive bullets to keep response latency snappy
    return cleaned_bullets[:10]


def _is_likely_header(line: str) -> bool:
    """Detects if a line is just a section title rather than an achievement bullet."""
    header_keywords = {
        "education", "experience", "work experience", "projects",
        "technical skills", "skills", "summary", "certifications",
        "achievements", "contact", "profile"
    }
    cleaned = line.lower().strip(" :-\t")
    return cleaned in header_keywords or len(line.split()) <= 2