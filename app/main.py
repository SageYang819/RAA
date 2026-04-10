from pathlib import Path
from app.parsers import parse_resume_text, parse_jd_text
from app.aligner import align_resume_to_jd
from app.rewrite_agent import rewrite_bullet
from app.rewrite_agent import apply_optimized_bullets

def read_text_file(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def main():
    resume_text = read_text_file("data/sample_resume.txt")
    jd_text = read_text_file("data/sample_jd.txt")

    resume = parse_resume_text(resume_text)
    jd = parse_jd_text(jd_text)

    print("\n=== Parsed Resume ===")
    print(resume.model_dump_json(indent=2))

    print("\n=== Parsed JD ===")
    print(jd.model_dump_json(indent=2))

    alignment = align_resume_to_jd(resume, jd)

    print("\n=== Alignment Result ===")
    print(alignment.model_dump_json(indent=2))

    print("\n=== Rewrite Test ===")

    from app.rewrite_agent import rewrite_bullet, select_best_bullet

    print("\n=== Rewrite Test (Improved) ===")

    jd_target = jd.required_skills[2]  # analyzing large datasets

    all_bullets = []
    for exp in resume.experience:
        all_bullets.extend(exp.bullets)

    best_bullet = select_best_bullet(all_bullets, jd_target)

    print("Selected bullet:", best_bullet)

    test_requirement = jd.required_skills[2]  # large dataset analysis

    result = rewrite_bullet(best_bullet, jd_target)

    print(result["rewritten_bullet"])
    print(result["reason"])

    from app.rewrite_agent import optimize_resume

    print("\n=== Full Resume Optimization ===")

    optimized = optimize_resume(resume, jd)

    for item in optimized:
        print("\n---")
        print("Skill:", item["skill"])
        print("Original:", item["original"])
        print("Rewritten:", item["rewritten"])
        print("Reason:", item["reason"])
    
    print("\n=== FINAL OPTIMIZED RESUME (EXPERIENCE) ===")

    new_experience = apply_optimized_bullets(resume, optimized)

    for exp in new_experience:
        print("\n", exp["company"], "-", exp["title"])
        for b in exp["bullets"]:
            print("•", b)

if __name__ == "__main__":
    main()