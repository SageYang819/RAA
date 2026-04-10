import json
import os
import re
from openai import OpenAI
from dotenv import load_dotenv

from app.schemas import ResumeSchema, JDSchema

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


CANONICAL_SECTION_LABELS = {
    "contact": "Contact",
    "summary": "Summary",
    "skills": "Skills",
    "languages": "Languages",
    "education": "Education",
    "experience": "Experience",
    "projects": "Projects",
    "certifications": "Certifications",
    "awards": "Awards",
    "publications": "Publications",
    "research": "Research",
    "volunteer experience": "Volunteer Experience",
    "leadership": "Leadership",
    "interests": "Interests",
    "custom": "Custom",
}


def split_string_items(value: str):
    text = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return []

    items = []
    for line in text.split("\n"):
        cleaned = re.sub(r"^[•●▪◦■\-]+\s*", "", line).strip()
        if cleaned:
            items.append(cleaned)

    return items


def split_long_project_text(text: str):
    text = text.strip()
    if not text:
        return []

    if "\n" in text:
        return split_string_items(text)

    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)
    cleaned_parts = [part.strip() for part in parts if part.strip()]
    return cleaned_parts if cleaned_parts else [text]


def ensure_list(value):
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [value]
    return []


def normalize_string_list(value):
    if isinstance(value, list):
        normalized = []
        for item in value:
            if isinstance(item, str):
                normalized.extend(split_string_items(item))
        return [x for x in normalized if x]

    if isinstance(value, str):
        return split_string_items(value)

    return []


def normalize_education(value):
    if isinstance(value, list):
        normalized = []
        for item in value:
            if isinstance(item, str):
                normalized.extend(split_string_items(item))

            elif isinstance(item, dict):
                degree = item.get("degree", "")
                school = item.get("institution", "") or item.get("school", "")
                dates = item.get("dates", "")

                text = " | ".join([x for x in [degree, school, dates] if x]).strip()
                if text:
                    normalized.append(text)

        return normalized

    if isinstance(value, str):
        return split_string_items(value)

    return []


def normalize_dict_of_lists(value):
    if not isinstance(value, dict):
        return {}

    normalized = {}
    for key, val in value.items():
        if not isinstance(key, str):
            continue
        cleaned_values = normalize_string_list(val)
        if cleaned_values:
            normalized[key.strip()] = cleaned_values

    return normalized


def canonicalize_section_label(label: str) -> str:
    if not isinstance(label, str) or not label.strip():
        return "Custom"

    lowered = label.strip().lower()
    return CANONICAL_SECTION_LABELS.get(lowered, "Custom")


def normalize_sections(value):
    sections = []

    if isinstance(value, dict):
        for title, content in value.items():
            cleaned_content = normalize_string_list(content)
            if cleaned_content:
                sections.append(
                    {
                        "original_title": str(title).strip(),
                        "canonical_label": canonicalize_section_label(str(title)),
                        "content": cleaned_content,
                    }
                )
        return sections

    if not isinstance(value, list):
        return sections

    for item in value:
        if isinstance(item, str):
            text_items = split_string_items(item)
            if text_items:
                sections.append(
                    {
                        "original_title": "Untitled Section",
                        "canonical_label": "Custom",
                        "content": text_items,
                    }
                )
            continue

        if isinstance(item, dict):
            original_title = (
                item.get("original_title")
                or item.get("title")
                or item.get("section_title")
                or item.get("name")
                or "Untitled Section"
            )

            raw_label = (
                item.get("canonical_label")
                or item.get("label")
                or item.get("mapped_label")
                or item.get("category")
                or original_title
            )

            content = (
                item.get("content")
                or item.get("items")
                or item.get("bullets")
                or item.get("lines")
                or item.get("entries")
                or item.get("description")
                or []
            )

            cleaned_content = normalize_string_list(content)

            if cleaned_content:
                sections.append(
                    {
                        "original_title": str(original_title).strip(),
                        "canonical_label": canonicalize_section_label(str(raw_label)),
                        "content": cleaned_content,
                    }
                )

    return sections


def normalize_experience_items(value):
    if not isinstance(value, list):
        return []

    normalized = []
    for item in value:
        if not isinstance(item, dict):
            continue

        bullets = normalize_string_list(item.get("bullets", []))

        normalized.append(
            {
                "company": str(item.get("company", "")).strip(),
                "location": str(item.get("location", "")).strip(),
                "title": str(item.get("title", "")).strip(),
                "dates": str(item.get("dates", "")).strip(),
                "bullets": bullets,
            }
        )

    return normalized


def normalize_project_items(value):
    if not isinstance(value, list):
        return []

    normalized = []
    for item in value:
        if not isinstance(item, dict):
            continue

        raw_descriptions = item.get("description", [])
        if isinstance(raw_descriptions, str):
            raw_descriptions = [raw_descriptions]

        descriptions = []
        if isinstance(raw_descriptions, list):
            for desc in raw_descriptions:
                if isinstance(desc, str):
                    descriptions.extend(split_long_project_text(desc))

        descriptions = [d.strip() for d in descriptions if d.strip()]

        normalized.append(
            {
                "name": str(item.get("name", "")).strip(),
                "description": descriptions,
            }
        )

    return normalized


def synthesize_sections_from_core(data: dict):
    synthesized = []

    if data.get("contact_info"):
        synthesized.append(
            {
                "original_title": "Contact",
                "canonical_label": "Contact",
                "content": data["contact_info"],
            }
        )

    if data.get("summary"):
        synthesized.append(
            {
                "original_title": "Summary",
                "canonical_label": "Summary",
                "content": [data["summary"]],
            }
        )

    skills = data.get("skills", {})
    if isinstance(skills, dict) and skills:
        skill_lines = []
        for category, values in skills.items():
            if values:
                skill_lines.append(f"{category}: {', '.join(values)}")
        if skill_lines:
            synthesized.append(
                {
                    "original_title": "Skills",
                    "canonical_label": "Skills",
                    "content": skill_lines,
                }
            )

    languages = data.get("languages", [])
    if languages:
        synthesized.append(
            {
                "original_title": "Languages",
                "canonical_label": "Languages",
                "content": languages,
            }
        )

    education = data.get("education", [])
    if education:
        synthesized.append(
            {
                "original_title": "Education",
                "canonical_label": "Education",
                "content": education,
            }
        )

    experiences = data.get("experience", [])
    if experiences:
        lines = []
        for exp in experiences:
            header_parts = [
                exp.get("company", ""),
                exp.get("location", ""),
                exp.get("title", ""),
                exp.get("dates", ""),
            ]
            header = " | ".join([x for x in header_parts if x]).strip(" |")
            if header:
                lines.append(header)
            lines.extend(exp.get("bullets", []))
        if lines:
            synthesized.append(
                {
                    "original_title": "Experience",
                    "canonical_label": "Experience",
                    "content": lines,
                }
            )

    projects = data.get("projects", [])
    if projects:
        lines = []
        for proj in projects:
            if proj.get("name"):
                lines.append(proj["name"])
            lines.extend(proj.get("description", []))
        if lines:
            synthesized.append(
                {
                    "original_title": "Projects",
                    "canonical_label": "Projects",
                    "content": lines,
                }
            )

    return synthesized


def backfill_core_fields_from_sections(data: dict):
    sections = data.get("sections", [])

    if not data.get("contact_info"):
        contact_lines = []
        for section in sections:
            if section.get("canonical_label") == "Contact":
                contact_lines.extend(section.get("content", []))
        if contact_lines:
            data["contact_info"] = contact_lines

    if not data.get("languages"):
        languages = []
        for section in sections:
            if section.get("canonical_label") == "Languages":
                for line in section.get("content", []):
                    parts = [p.strip() for p in line.split(",") if p.strip()]
                    if parts:
                        languages.extend(parts)
                    else:
                        languages.append(line)
        if languages:
            data["languages"] = languages

    if not data.get("education"):
        education = []
        for section in sections:
            if section.get("canonical_label") == "Education":
                education.extend(section.get("content", []))
        if education:
            data["education"] = education

    if not data.get("summary"):
        for section in sections:
            if section.get("canonical_label") == "Summary" and section.get("content"):
                data["summary"] = section["content"][0]
                break

    if not data.get("skills"):
        for section in sections:
            if section.get("canonical_label") == "Skills" and section.get("content"):
                data["skills"] = {"General": section["content"]}
                break

    return data


def extract_json_from_response(content: str) -> dict:
    content = content.strip()

    if content.startswith("```json"):
        content = content.removeprefix("```json").removesuffix("```").strip()
    elif content.startswith("```"):
        content = content.removeprefix("```").removesuffix("```").strip()

    return json.loads(content)


def parse_resume_text(resume_text: str) -> ResumeSchema:
    prompt = f"""
You are an information extraction system.

Extract the following resume into structured JSON with these exact keys:
- name
- contact_info
- summary
- skills
- languages
- experience
- projects
- education
- sections

Rules:
- Return valid JSON only.
- Do not invent information.
- Preserve all meaningful resume content.
- Do NOT drop content just because it does not fit a fixed schema.
- Use the standard fields when the content clearly fits them.
- Also return a full section list in "sections" so the original resume structure is preserved.
- Contact lines such as location, phone, email, GitHub, and LinkedIn should go into contact_info, not summary.
- For each experience item, keep location separately if available.
- For projects, each project description must be returned as a LIST of short bullet-like items, not one long paragraph.
- Do NOT collapse multiple project bullets into one sentence.

Expected structure:
- name: string
- contact_info: list of strings
- summary: string
- skills: object where each key is a category and each value is a list of strings
- languages: list of strings
- experience: list of objects with keys:
  - company
  - location
  - title
  - dates
  - bullets
- projects: list of objects with keys:
  - name
  - description
- education: list of strings
- sections: list of objects with keys:
  - original_title
  - canonical_label
  - content

Allowed canonical_label values:
- Contact
- Summary
- Skills
- Languages
- Education
- Experience
- Projects
- Certifications
- Awards
- Publications
- Research
- Volunteer Experience
- Leadership
- Interests
- Custom

Resume text:
{resume_text}
"""

    response = client.responses.create(
        model="gpt-5-mini",
        input=prompt,
    )

    content = response.output_text
    data = extract_json_from_response(content)

    data["contact_info"] = normalize_string_list(data.get("contact_info", []))
    data["education"] = normalize_education(data.get("education", []))
    data["languages"] = normalize_string_list(data.get("languages", []))
    data["skills"] = normalize_dict_of_lists(data.get("skills", {}))
    data["experience"] = normalize_experience_items(data.get("experience", []))
    data["projects"] = normalize_project_items(data.get("projects", []))
    data["sections"] = normalize_sections(data.get("sections", []))

    if not data["sections"]:
        data["sections"] = synthesize_sections_from_core(data)

    data = backfill_core_fields_from_sections(data)

    return ResumeSchema.model_validate(data)


def parse_jd_text(jd_text: str) -> JDSchema:
    prompt = f"""
You are an information extraction system.

Extract the following job description into structured JSON with these exact keys:
- job_title
- company
- required_skills
- preferred_skills
- responsibilities
- keywords

Rules:
- Return valid JSON only.
- Do not invent information.
- Only use information explicitly stated or strongly implied in the JD.
- Keep skill names concise.

Job description:
{jd_text}
"""

    response = client.responses.create(
        model="gpt-5-mini",
        input=prompt,
    )

    content = response.output_text
    data = extract_json_from_response(content)

    return JDSchema.model_validate(data)