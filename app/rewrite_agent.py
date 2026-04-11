from openai import OpenAI
import os
from dotenv import load_dotenv
import json

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def rewrite_bullet(bullet: str, jd_requirement: str, strict_preserve_mode: bool = False) -> dict:
    preserve_rule = """
- Keep the rewritten sentence as close as possible to the original wording and structure.
- Only make minimal edits: surface the JD-relevant angle, sharpen the impact verb if needed.
- Do NOT restructure the sentence or change its core meaning.
""" if strict_preserve_mode else """
- Restructure the bullet if needed to lead with the most JD-relevant action or outcome.
- Strengthen the impact verb to be more specific and results-oriented (e.g. "Drove", "Delivered", "Reduced", "Scaled").
- If the original bullet has a quantified result, preserve it exactly — do not alter numbers.
- If no metric exists, do NOT fabricate one.
- Use the JD requirement's language and framing where it genuinely reflects what the original bullet describes.
"""

    prompt = f"""
You are a senior resume strategist helping a candidate tailor their resume for a specific job.

Your task:
Rewrite ONE resume bullet so it clearly demonstrates the candidate's fit for the target job requirement.
The rewrite must feel like it was written FOR this specific job — not a generic polish.

=== STRICT RULES (never violate) ===
- Do NOT invent experience, tools, technologies, certifications, or qualifications not in the original.
- Do NOT add language or communication skill claims unless clearly present in the original.
- Do NOT fabricate metrics, numbers, or scale.
- Do NOT add collaborators, teams, or stakeholders not mentioned in the original.
- The rewritten bullet must be grounded in what the original bullet actually describes.

=== QUALITY RULES ===
{preserve_rule}
- The rewrite must clearly show relevance to the job requirement — a recruiter should immediately see the connection.
- Lead with a strong past-tense action verb.
- Remove filler phrases like "Responsible for" or "Helped with".
- Keep it to 1–2 concise sentences.

=== INPUTS ===
Original bullet:
{bullet}

Target job requirement:
{jd_requirement}

=== OUTPUT ===
Return ONLY valid JSON, no markdown:
{{
  "rewritten_bullet": "...",
  "reason": "One sentence explaining what was changed and why it better matches the JD requirement."
}}
"""

    response = client.responses.create(
        model="gpt-4o-mini",
        input=prompt,
    )

    content = response.output_text.strip()

    if content.startswith("```"):
        content = content.strip("```").strip()
        if content.startswith("json"):
            content = content[4:].strip()

    try:
        return json.loads(content)
    except Exception:
        return {
            "rewritten_bullet": bullet,
            "reason": "Failed to parse model output",
        }


def select_best_bullet(bullets: list[str], jd_requirement: str) -> str | None:
    """
    Use LLM to select the most relevant bullet for a given JD requirement.
    Falls back to keyword scoring if LLM call fails.
    """
    if not bullets:
        return None

    numbered = "\n".join(f"{i+1}. {b}" for i, b in enumerate(bullets))

    prompt = f"""
You are a resume alignment expert.

Given the list of resume bullets below, select the ONE bullet that is MOST relevant to the target job requirement.
Choose the bullet whose underlying experience most closely supports the requirement — even if the wording differs.
If no bullet is relevant, reply with 0.

Job requirement:
{jd_requirement}

Resume bullets:
{numbered}

Reply with ONLY the number of the best bullet (e.g. "3"), or "0" if none are relevant.
"""

    try:
        response = client.responses.create(
            model="gpt-4o-mini",
            input=prompt,
        )
        answer = response.output_text.strip().strip(".")
        idx = int(answer) - 1
        if 0 <= idx < len(bullets):
            return bullets[idx]
    except Exception:
        pass

    # Fallback: keyword scoring
    jd_words = [w for w in jd_requirement.lower().split() if len(w) > 3]
    best_bullet = None
    best_score = 0

    for bullet in bullets:
        score = sum(1 for w in jd_words if w in bullet.lower())
        if score > best_score:
            best_score = score
            best_bullet = bullet

    return best_bullet if best_score > 0 else None


def rewrite_summary(original_summary: str, jd: object, strict_preserve_mode: bool = False) -> str:
    """
    Rewrite the resume summary to reflect the candidate's fit for this specific JD.
    """
    job_title = getattr(jd, "job_title", "") or ""
    company = getattr(jd, "company", "") or ""
    required_skills = getattr(jd, "required_skills", []) or []
    responsibilities = getattr(jd, "responsibilities", []) or []
    keywords = getattr(jd, "keywords", []) or []

    jd_context = f"Job Title: {job_title}"
    if company:
        jd_context += f"\nCompany: {company}"
    if required_skills:
        jd_context += f"\nKey Requirements: {', '.join(required_skills[:8])}"
    if responsibilities:
        jd_context += f"\nCore Responsibilities: {'; '.join(responsibilities[:4])}"
    if keywords:
        jd_context += f"\nKeywords: {', '.join(keywords[:10])}"

    preserve_note = (
        "Keep close to the original structure and length. Only adjust framing to surface JD relevance."
        if strict_preserve_mode else
        "Reframe the summary to clearly position the candidate for THIS specific role. "
        "It should read like a targeted pitch, not a generic bio."
    )

    prompt = f"""
You are a senior resume strategist.

Rewrite the candidate's resume summary so it is clearly tailored for the target job below.
The new summary should make a recruiter immediately see why this candidate fits this role.

=== RULES ===
- Do NOT invent experience, skills, or qualifications not implied by the original summary.
- Naturally incorporate 2–4 of the JD's key terms where they genuinely reflect the candidate's background.
- Keep it to 3–5 sentences.
- Do NOT start with "I" or the candidate's name.
- {preserve_note}

=== ORIGINAL SUMMARY ===
{original_summary}

=== TARGET JOB ===
{jd_context}

Return ONLY the rewritten summary text. No JSON, no labels, no explanation.
"""

    try:
        response = client.responses.create(
            model="gpt-4o-mini",
            input=prompt,
        )
        return response.output_text.strip()
    except Exception:
        return original_summary


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
