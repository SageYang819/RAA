from typing import Any, Dict, List

from app.parsers import parse_resume_text, parse_jd_text
from app.aligner import align_resume_to_jd
from app.rewrite_agent import optimize_resume, apply_optimized_bullets
from app.normalizers import normalize_resume_text_to_markdown, normalize_jd_text_to_markdown


CORE_SECTION_LABELS = {
    "contact",
    "summary",
    "skills",
    "languages",
    "education",
    "experience",
    "projects",
}


def generate_warnings(alignment, optimized: List[Dict[str, Any]]) -> List[str]:
    warnings = []

    if getattr(alignment, "missing_skills", None):
        for skill in alignment.missing_skills:
            warnings.append(
                f"JD mentions '{skill}', but the resume does not provide strong direct evidence for it."
            )

    if not optimized:
        warnings.append("No safe rewrite suggestions were generated.")

    optimized_skills = {item["skill"] for item in optimized}
    for skill in getattr(alignment, "missing_skills", []):
        if skill not in optimized_skills:
            warnings.append(
                f"No safe rewrite was applied for '{skill}' because no sufficiently relevant bullet was found."
            )

    warnings.append("Please review the final output before submitting it to employers.")

    deduped = []
    seen = set()
    for w in warnings:
        if w not in seen:
            deduped.append(w)
            seen.add(w)

    return deduped


def build_change_log(
    optimized: List[Dict[str, Any]],
    selected_indices: List[int],
) -> List[Dict[str, Any]]:
    selected_set = set(selected_indices)
    change_log = []

    for idx, item in enumerate(optimized):
        change_log.append(
            {
                "target_requirement": item["skill"],
                "original": item["original"],
                "rewritten": item["rewritten"],
                "reason": item["reason"],
                "applied": idx in selected_set,
            }
        )

    return change_log


def build_final_resume(resume, final_experience) -> Dict[str, Any]:
    serialized_projects = [
        {
            "name": proj.name,
            "description": proj.description,
        }
        for proj in getattr(resume, "projects", [])
    ]

    serialized_sections = [
        {
            "original_title": section.original_title,
            "canonical_label": section.canonical_label,
            "content": section.content,
        }
        for section in getattr(resume, "sections", [])
    ]

    return {
        "name": getattr(resume, "name", ""),
        "contact_info": getattr(resume, "contact_info", []),
        "summary": getattr(resume, "summary", ""),
        "skills": getattr(resume, "skills", {}),
        "languages": getattr(resume, "languages", []),
        "education": getattr(resume, "education", []),
        "experience": final_experience,
        "projects": serialized_projects,
        "sections": serialized_sections,
    }


def extra_sections_for_render(final_resume: Dict[str, Any]) -> List[Dict[str, Any]]:
    extra_sections = []
    resume_name = final_resume.get("name", "").strip().lower()

    for section in final_resume.get("sections", []):
        label = section.get("canonical_label", "").strip().lower()
        title = section.get("original_title", "").strip().lower()
        content = [str(item).strip() for item in section.get("content", []) if str(item).strip()]

        if label in CORE_SECTION_LABELS:
            continue

        if title in CORE_SECTION_LABELS:
            continue

        if resume_name:
            if title == resume_name:
                continue
            if len(content) == 1 and content[0].lower() == resume_name:
                continue

        extra_sections.append(section)

    return extra_sections


def render_resume_text(final_resume: Dict[str, Any]) -> str:
    lines: List[str] = []

    if final_resume.get("name"):
        lines.append(final_resume["name"])

    contact_info = final_resume.get("contact_info", [])
    if contact_info:
        lines.extend(contact_info)

    if final_resume.get("name") or contact_info:
        lines.append("")

    lines.append("Summary")
    lines.append(final_resume.get("summary", "") or "")
    lines.append("")

    lines.append("Skills")
    skills = final_resume.get("skills", {})
    if skills:
        for category, values in skills.items():
            pretty_category = category.replace("_", " ").title()
            lines.append(f"{pretty_category}: {', '.join(values)}")
    lines.append("")

    lines.append("Languages")
    languages = final_resume.get("languages", [])
    if languages:
        lines.append(", ".join(languages))
    lines.append("")

    lines.append("Education")
    education = final_resume.get("education", [])
    if education:
        for item in education:
            lines.append(f"- {item}")
    lines.append("")

    lines.append("Experience")
    for exp in final_resume.get("experience", []):
        header_parts = [exp.get("company", ""), exp.get("location", ""), exp.get("title", "")]
        header = " — ".join([x for x in header_parts if x])
        dates = exp.get("dates", "")
        if dates:
            header = f"{header} ({dates})" if header else f"({dates})"

        lines.append(header)
        for bullet in exp.get("bullets", []):
            lines.append(f"- {bullet}")
        lines.append("")

    projects = final_resume.get("projects", [])
    if projects:
        lines.append("Projects")
        for proj in projects:
            if proj.get("name"):
                lines.append(proj["name"])
            for desc in proj.get("description", []):
                lines.append(f"- {desc}")
        lines.append("")

    for section in extra_sections_for_render(final_resume):
        title = section.get("original_title") or section.get("canonical_label") or "Other"
        lines.append(title)
        for item in section.get("content", []):
            lines.append(f"- {item}")
        lines.append("")

    return "\n".join(lines).strip()


def render_resume_markdown(final_resume: Dict[str, Any]) -> str:
    lines: List[str] = []

    if final_resume.get("name"):
        lines.append(f"# {final_resume['name']}")

    contact_info = final_resume.get("contact_info", [])
    if contact_info:
        lines.append("")
        for item in contact_info:
            lines.append(item)

    if final_resume.get("name") or contact_info:
        lines.append("")

    lines.append("## Summary")
    lines.append(final_resume.get("summary", "") or "")
    lines.append("")

    lines.append("## Skills")
    skills = final_resume.get("skills", {})
    if skills:
        for category, values in skills.items():
            pretty_category = category.replace("_", " ").title()
            lines.append(f"**{pretty_category}:** {', '.join(values)}")
    lines.append("")

    lines.append("## Languages")
    languages = final_resume.get("languages", [])
    if languages:
        lines.append(", ".join(languages))
    lines.append("")

    lines.append("## Education")
    education = final_resume.get("education", [])
    if education:
        for item in education:
            lines.append(f"- {item}")
    lines.append("")

    lines.append("## Experience")
    for exp in final_resume.get("experience", []):
        header_parts = [exp.get("company", ""), exp.get("location", ""), exp.get("title", "")]
        header = " — ".join([x for x in header_parts if x])
        dates = exp.get("dates", "")
        if dates:
            header = f"{header} ({dates})" if header else f"({dates})"

        lines.append(f"### {header}")
        for bullet in exp.get("bullets", []):
            lines.append(f"- {bullet}")
        lines.append("")

    projects = final_resume.get("projects", [])
    if projects:
        lines.append("## Projects")
        for proj in projects:
            if proj.get("name"):
                lines.append(f"### {proj['name']}")
            for desc in proj.get("description", []):
                lines.append(f"- {desc}")
            lines.append("")

    for section in extra_sections_for_render(final_resume):
        title = section.get("original_title") or section.get("canonical_label") or "Other"
        lines.append(f"## {title}")
        for item in section.get("content", []):
            lines.append(f"- {item}")
        lines.append("")

    return "\n".join(lines).strip()


def run_resume_optimization(
    resume_text: str,
    jd_text: str,
    selected_indices: List[int] | None = None,
    strict_preserve_mode: bool = False,
) -> Dict[str, Any]:
    normalized_resume_text = normalize_resume_text_to_markdown(resume_text)
    normalized_jd_text = normalize_jd_text_to_markdown(jd_text)

    resume = parse_resume_text(normalized_resume_text)
    jd = parse_jd_text(normalized_jd_text)
    alignment = align_resume_to_jd(resume, jd)
    optimized = optimize_resume(resume, jd, strict_preserve_mode=strict_preserve_mode)

    if selected_indices is None:
        selected_indices = list(range(len(optimized)))

    selected_optimized = [
        item for idx, item in enumerate(optimized) if idx in selected_indices
    ]

    final_experience = apply_optimized_bullets(resume, selected_optimized)
    final_resume = build_final_resume(resume, final_experience)
    warnings = generate_warnings(alignment, selected_optimized)
    change_log = build_change_log(optimized, selected_indices)

    return {
        "normalized_resume_text": normalized_resume_text,
        "normalized_jd_text": normalized_jd_text,
        "parsed_resume": resume,
        "parsed_jd": jd,
        "alignment": alignment,
        "optimized": optimized,
        "selected_optimized": selected_optimized,
        "final_resume": final_resume,
        "final_resume_text": render_resume_text(final_resume),
        "final_resume_markdown": render_resume_markdown(final_resume),
        "warnings": warnings,
        "change_log": change_log,
    }