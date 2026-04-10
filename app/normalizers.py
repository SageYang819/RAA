import re
from typing import Dict, List


RESUME_SECTION_ALIASES: Dict[str, str] = {
    "contact": "Contact",
    "contact information": "Contact",
    "contact info": "Contact",
    "summary": "Summary",
    "profile": "Summary",
    "professional summary": "Summary",
    "about": "Summary",
    "skills": "Skills",
    "technical skills": "Skills",
    "core skills": "Skills",
    "key skills": "Skills",
    "core competencies": "Skills",
    "competencies": "Skills",
    "languages": "Languages",
    "language": "Languages",
    "spoken languages": "Languages",
    "language skills": "Languages",
    "experience": "Experience",
    "work experience": "Experience",
    "professional experience": "Experience",
    "employment": "Experience",
    "career history": "Experience",
    "projects": "Projects",
    "project experience": "Projects",
    "selected projects": "Projects",
    "project experience & leadership": "Projects",
    "education": "Education",
    "academic background": "Education",
    "certifications": "Certifications",
    "certification": "Certifications",
    "awards": "Awards",
    "publications": "Publications",
    "research": "Research",
    "volunteer experience": "Volunteer Experience",
    "leadership": "Leadership",
    "interests": "Interests",
}


JD_SECTION_ALIASES: Dict[str, str] = {
    "job title": "Job Title",
    "about the role": "Overview",
    "overview": "Overview",
    "summary": "Overview",
    "responsibilities": "Responsibilities",
    "what you'll do": "Responsibilities",
    "what you will do": "Responsibilities",
    "requirements": "Requirements",
    "qualifications": "Requirements",
    "required qualifications": "Requirements",
    "preferred qualifications": "Preferred Qualifications",
    "preferred skills": "Preferred Qualifications",
    "nice to have": "Preferred Qualifications",
}


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_line(line: str) -> str:
    line = line.strip()
    line = re.sub(r"^[•●▪◦■\-]+\s*", "- ", line)
    return line


def canonical_resume_heading(line: str) -> str | None:
    lowered = line.lower().strip().strip(":")
    return RESUME_SECTION_ALIASES.get(lowered)


def canonical_jd_heading(line: str) -> str | None:
    lowered = line.lower().strip().strip(":")
    return JD_SECTION_ALIASES.get(lowered)


def split_lines(text: str) -> List[str]:
    return [normalize_line(line) for line in clean_text(text).split("\n") if line.strip()]


def looks_like_contact_line(line: str) -> bool:
    lowered = line.lower()

    if "@" in line:
        return True
    if "linkedin" in lowered or "github" in lowered:
        return True
    if "http://" in lowered or "https://" in lowered or "www." in lowered:
        return True
    if "|" in line:
        return True
    if re.search(r"\+?\d[\d\-\s]{6,}", line):
        return True

    return False


def emit_section(output: List[str], title: str, content_lines: List[str]) -> None:
    if not content_lines:
        return

    output.append(f"## {title}")
    output.append("")
    output.extend(content_lines)
    output.append("")


def normalize_resume_text_to_markdown(raw_text: str) -> str:
    lines = split_lines(raw_text)

    if not lines:
        return ""

    output: List[str] = []

    candidate_name = lines[0]
    output.append(f"# {candidate_name}")
    output.append("")

    pre_heading_lines: List[str] = []
    found_any_heading = False
    current_section = None

    for line in lines[1:]:
        canonical_heading = canonical_resume_heading(line)

        if canonical_heading:
            if not found_any_heading and pre_heading_lines:
                contact_lines = [x for x in pre_heading_lines if looks_like_contact_line(x)]
                other_lines = [x for x in pre_heading_lines if not looks_like_contact_line(x)]

                emit_section(output, "Contact", contact_lines)
                emit_section(output, "Summary", other_lines)

                pre_heading_lines = []

            found_any_heading = True
            current_section = canonical_heading
            output.append(f"## {canonical_heading}")
            output.append("")
            continue

        if not found_any_heading:
            pre_heading_lines.append(line)
            continue

        if current_section is None:
            current_section = "Summary"
            output.append("## Summary")
            output.append("")

        output.append(line)

    if pre_heading_lines:
        contact_lines = [x for x in pre_heading_lines if looks_like_contact_line(x)]
        other_lines = [x for x in pre_heading_lines if not looks_like_contact_line(x)]

        emit_section(output, "Contact", contact_lines)
        emit_section(output, "Summary", other_lines)

    return "\n".join(output).strip()


def normalize_jd_text_to_markdown(raw_text: str) -> str:
    lines = split_lines(raw_text)

    if not lines:
        return ""

    output: List[str] = []
    current_section = None

    first_line = lines[0]
    output.append(f"# {first_line}")
    output.append("")

    for line in lines[1:]:
        canonical_heading = canonical_jd_heading(line)

        if canonical_heading:
            current_section = canonical_heading
            output.append(f"## {canonical_heading}")
            output.append("")
            continue

        if current_section is None:
            current_section = "Overview"
            output.append("## Overview")
            output.append("")

        output.append(line)

    return "\n".join(output).strip()