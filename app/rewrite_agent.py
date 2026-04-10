from openai import OpenAI
import os
from dotenv import load_dotenv
import json

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def rewrite_bullet(bullet: str, jd_requirement: str, strict_preserve_mode: bool = False) -> dict:
    preserve_rule = """
- Keep the rewritten sentence as close as possible to the original wording.
- Only make minimal edits for clarity and JD alignment.
""" if strict_preserve_mode else """
- You MAY improve clarity, wording, and conciseness.
- You MAY generalize scale only if clearly reasonable from the original bullet.
- Prefer safer rewriting over aggressive keyword stuffing.
- If the JD requirement is only weakly supported by the original bullet, keep the rewrite conservative.
"""

    prompt = f"""
You are a professional resume rewriting assistant.

Your task:
Rewrite the resume bullet to better match the job requirement.

Strict rules:
- Do NOT invent new experience.
- Do NOT add tools, technologies, qualifications, languages, certifications, or collaborations not explicitly supported by the original bullet.
- Do NOT add language claims such as English communication, bilingual communication, verbal communication, written communication, stakeholder communication, or presentation skills unless clearly present in the original bullet.
- Do NOT claim direct use of tools (for example SQL, Python, Excel, Power BI) unless clearly present in the original bullet.
{preserve_rule}

Original bullet:
{bullet}

Target job requirement:
{jd_requirement}

Return ONLY valid JSON:
{{
  "rewritten_bullet": "...",
  "reason": "..."
}}
"""

    response = client.responses.create(
        model="gpt-5-mini",
        input=prompt,
    )

    content = response.output_text.strip()

    if content.startswith("```"):
        content = content.strip("```").strip()

    try:
        return json.loads(content)
    except Exception:
        return {
            "rewritten_bullet": bullet,
            "reason": "Failed to parse model output",
        }


def select_best_bullet(bullets: list[str], jd_requirement: str) -> str | None:
    jd_words = jd_requirement.lower().split()

    best_bullet = None
    best_score = 0

    for bullet in bullets:
        score = sum(1 for w in jd_words if w in bullet.lower())
        if score > best_score:
            best_score = score
            best_bullet = bullet

    if best_score > 0:
        return best_bullet

    fallback_keywords = ["data", "analysis", "report", "risk", "model", "dashboard"]

    for bullet in bullets:
        if any(k in bullet.lower() for k in fallback_keywords):
            return bullet

    return None


def optimize_resume(resume, jd, strict_preserve_mode: bool = False):
    results = []
    used_bullets = set()

    all_bullets = []
    for exp in resume.experience:
        all_bullets.extend(exp.bullets)

    for skill in jd.required_skills:
        best_bullet = select_best_bullet(all_bullets, skill)

        if best_bullet is None:
            continue

        if best_bullet in used_bullets:
            continue

        used_bullets.add(best_bullet)

        rewritten = rewrite_bullet(
            best_bullet,
            skill,
            strict_preserve_mode=strict_preserve_mode,
        )

        results.append(
            {
                "skill": skill,
                "original": best_bullet,
                "rewritten": rewritten["rewritten_bullet"],
                "reason": rewritten["reason"],
            }
        )

    return results


def apply_optimized_bullets(resume, optimized_results):
    rewrite_map = {
        item["original"]: item["rewritten"]
        for item in optimized_results
    }

    new_experience = []

    for exp in resume.experience:
        new_bullets = []

        for bullet in exp.bullets:
            if bullet in rewrite_map:
                new_bullets.append(rewrite_map[bullet])
            else:
                new_bullets.append(bullet)

        new_experience.append(
            {
                "company": exp.company,
                "location": exp.location,
                "title": exp.title,
                "dates": exp.dates,
                "bullets": new_bullets,
            }
        )

    return new_experience