from app.schemas import ResumeSchema, JDSchema, SkillMatch, AlignmentResult


def collect_resume_text_chunks(resume: ResumeSchema) -> list[str]:
    chunks = []

    if resume.name:
        chunks.append(resume.name)

    chunks.extend(resume.contact_info)

    if resume.summary:
        chunks.append(resume.summary)

    for _, skill_list in resume.skills.items():
        chunks.extend(skill_list)

    chunks.extend(resume.languages)

    for exp in resume.experience:
        if exp.company:
            chunks.append(exp.company)
        if exp.title:
            chunks.append(exp.title)
        chunks.extend(exp.bullets)

    for project in resume.projects:
        if project.name:
            chunks.append(project.name)
        chunks.extend(project.description)

    chunks.extend(resume.education)

    for section in resume.sections:
        if section.original_title:
            chunks.append(section.original_title)
        chunks.extend(section.content)

    return [c.lower() for c in chunks if c]


def align_resume_to_jd(resume: ResumeSchema, jd: JDSchema) -> AlignmentResult:
    chunks = collect_resume_text_chunks(resume)
    all_text = " ".join(chunks)

    matched_skills = []
    missing_skills = []

    for skill in jd.required_skills:
        skill_lower = skill.lower()
        evidence = [c for c in chunks if skill_lower in c]

        matched = len(evidence) > 0
        if not matched:
            missing_skills.append(skill)

        matched_skills.append(
            SkillMatch(
                skill=skill,
                matched=matched,
                evidence=evidence[:3],
                gap_reason="" if matched else f"{skill} not found in resume",
            )
        )

    matched_responsibilities = []

    for resp in jd.responsibilities:
        resp_lower = resp.lower()
        if any(word in all_text for word in resp_lower.split()):
            matched_responsibilities.append(resp)

    return AlignmentResult(
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        matched_responsibilities=matched_responsibilities,
    )