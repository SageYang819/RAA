from openai import OpenAI
import os
from dotenv import load_dotenv
import json

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def rewrite_bullet(
    bullet: str,
    jd_requirement: str,
    jd_responsibilities: list[str] = None,
    strict_preserve_mode: bool = False,
) -> dict:
    preserve_rule = """
- Keep the rewritten sentence as close as possible to the original wording and structure.
- Only make minimal edits: surface the JD-relevant angle, sharpen the impact verb if needed.
- Do NOT restructure the sentence or change its core meaning.
""" if strict_preserve_mode else """
- Restructure the bullet if needed to lead with the most JD-relevant action or outcome.
- Strengthen the impact verb to be more specific and results-oriented (e.g. "Drove", "Delivered", "Reduced", "Scaled").
- If the original bullet has a quantified result, preserve it exactly — do not alter numbers.
- Use the JD's language and framing where it genuinely reflects what the original bullet describes.
"""

    # Build responsibilities context block
    responsibilities_block = ""
    if jd_responsibilities:
        resp_lines = "\n".join(f"- {r}" for r in jd_responsibilities[:8])
        responsibilities_block = f"""
JD Responsibilities (for framing reference only — use this language if the original bullet genuinely supports it):
{resp_lines}
"""

    prompt = f"""
You are a senior resume strategist helping a candidate tailor their resume for a specific job.

Your task:
Rewrite ONE resume bullet so it clearly demonstrates the candidate's fit for the target job requirement.
The rewrite must reflect what the candidate ACTUALLY DID — not what the job requires.
Use the JD's language and framing only where the original bullet genuinely supports it.

=== ABSOLUTE RULES (never violate, no exceptions) ===
- You are working ONLY with what is in the original bullet. That is your only source of truth.
- Do NOT invent tools, technologies, systems, certifications, or qualifications not in the original.
- Do NOT add any claims about communication, collaboration, stakeholders, or teamwork unless clearly stated in the original bullet.
- Do NOT fabricate metrics, numbers, percentages, or scale.
- Do NOT add any new skills, responsibilities, or activities not described in the original bullet.
- If the original bullet only weakly relates to the JD requirement, make only minimal surface-level adjustments. Do not force a strong claim.
- The test: could a fact-checker verify every word of the rewrite from the original bullet alone? If not, remove it.

=== QUALITY RULES ===
{preserve_rule}
- Lead with a strong past-tense action verb.
- Remove filler phrases like "Responsible for" or "Helped with".
- The rewrite should make the JD relevance visible — a recruiter reading this bullet should immediately see the connection to the requirement.
- Keep it to 1–2 concise sentences.
{responsibilities_block}
=== INPUTS ===
Original bullet:
{bullet}

Target job requirement:
{jd_requirement}

=== OUTPUT ===
Return ONLY valid JSON, no markdown:
{{
  "rewritten_bullet": "...",
  "reason": "One sentence: what angle was emphasized and why it matches the JD requirement — based only on what was in the original bullet."
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

Given the list of resume bullets below, select the ONE bullet whose underlying experience
most closely supports the target job requirement — even if the wording differs.

If no bullet is meaningfully relevant, reply with 0.

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


def rewrite_summary(
    original_summary: str,
    jd: object,
    strict_preserve_mode: bool = False,
) -> str:
    """
    Rewrite the resume summary to reflect the candidate's fit for this specific JD.
    Only uses information present in the original summary.
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
        jd_context += f"\nCore Responsibilities:\n" + "\n".join(f"- {r}" for r in responsibilities[:6])
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

Rewrite the candidate's summary so it is clearly tailored for the target job below.

=== ABSOLUTE RULES ===
- You are working ONLY from the original summary. Do NOT add skills, experience, or qualifications not present in it.
- Every claim in the rewrite must be verifiable from the original summary alone.
- Do NOT fabricate numbers, titles, tools, or achievements.
- Naturally incorporate 2–4 of the JD's key terms ONLY where they genuinely reflect what is already in the summary.
- Do NOT use meta-language that references the JD directly. Banned phrases include: "aligns with", "as required by", "in accordance with the requirements", "to meet the needs of", "as needed for this role", or any phrasing that makes the summary sound like it is responding to a job posting rather than describing the candidate.

=== QUALITY RULES ===
- Keep it to 3–5 sentences.
- Do NOT start with "I" or the candidate's name.
- {preserve_note}
- Make it immediately clear to a recruiter why this candidate fits THIS specific role.

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

    # Pass JD responsibilities to rewrite_bullet for better framing
    jd_responsibilities = getattr(jd, "responsibilities", []) or []

    for skill in jd.required_skills:
        best_bullet = select_best_bullet(all_bullets, skill)

        if best_bullet is None:
            continue

        if best_bullet in used_bullets:
            continue

        used_bullets.add(best_bullet)

        rewritten = rewrite_bullet(
            bullet=best_bullet,
            jd_requirement=skill,
            jd_responsibilities=jd_responsibilities,
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
