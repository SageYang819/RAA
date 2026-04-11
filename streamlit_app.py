import streamlit as st
from app.services import run_resume_optimization, extra_sections_for_render
from app.file_extractors import extract_resume_text_from_uploaded_file
from app.jd_extractors import resolve_jd_input
from app.docx_exporter import build_docx_bytes

st.set_page_config(page_title="AI Resume Alignment Agent", layout="wide")

# ── Custom CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Metric cards */
.metric-card {
    background: #f8f9fa;
    border-radius: 10px;
    padding: 16px 20px;
    text-align: center;
}
.metric-label {
    font-size: 12px;
    color: #888;
    margin-bottom: 4px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.metric-value {
    font-size: 26px;
    font-weight: 600;
    color: #111;
}
.metric-value.green { color: #2e7d32; }
.metric-value.amber { color: #e65100; }

/* Summary compare */
.compare-box {
    background: #f8f9fa;
    border-radius: 10px;
    padding: 14px 16px;
    font-size: 14px;
    line-height: 1.65;
    color: #222;
    height: 100%;
}
.compare-label {
    font-size: 11px;
    color: #888;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 8px;
    font-weight: 600;
}
.badge-new {
    display: inline-block;
    background: #e8f5e9;
    color: #2e7d32;
    font-size: 10px;
    padding: 2px 8px;
    border-radius: 6px;
    margin-left: 6px;
    font-weight: 600;
}

/* Bullet suggestion cards */
.bullet-card {
    border: 1px solid #eee;
    border-radius: 10px;
    padding: 14px 16px;
    margin-bottom: 10px;
    background: #fff;
}
.bullet-orig {
    font-size: 13px;
    color: #aaa;
    text-decoration: line-through;
    margin-bottom: 6px;
}
.bullet-new {
    font-size: 14px;
    color: #111;
    line-height: 1.6;
    margin-bottom: 6px;
}
.bullet-reason {
    font-size: 12px;
    color: #888;
}
.skill-tag {
    display: inline-block;
    background: #e3f2fd;
    color: #1565c0;
    font-size: 11px;
    padding: 2px 10px;
    border-radius: 12px;
    margin-bottom: 8px;
    font-weight: 500;
}

/* Section headers */
.section-header {
    font-size: 13px;
    font-weight: 600;
    color: #555;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 10px;
    padding-bottom: 6px;
    border-bottom: 1px solid #eee;
}

/* Hide default Streamlit top padding */
.block-container { padding-top: 2rem !important; }
</style>
""", unsafe_allow_html=True)


# ── Session state defaults ───────────────────────────────────────────────────
defaults = {
    "resume_text": "",
    "jd_text": "",
    "jd_url": "",
    "resolved_jd_text": "",
    "pipeline_ran": False,
    "result": None,
    "selected_indices": [],
    "uploaded_resume_name": "",
    "strict_preserve_mode": False,
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


def reset_app():
    widget_keys = {"resume_text", "jd_text", "jd_url", "strict_preserve_mode"}
    for key in widget_keys:
        st.session_state.pop(key, None)
    for key, value in defaults.items():
        if key not in widget_keys:
            st.session_state[key] = value


# ── Header ───────────────────────────────────────────────────────────────────
col_title, col_reset = st.columns([6, 1])
with col_title:
    st.markdown("## AI Resume Alignment Agent")
    st.caption("Upload your resume and a job description — get a tailored resume in seconds.")
with col_reset:
    st.write("")
    if st.button("Reset", use_container_width=True):
        reset_app()
        st.rerun()

st.divider()

# ── Input: Left / Right ──────────────────────────────────────────────────────
col_resume, col_jd = st.columns(2, gap="large")

with col_resume:
    st.markdown('<div class="section-header">Resume</div>', unsafe_allow_html=True)

    uploaded_resume = st.file_uploader(
        "Upload file",
        type=["txt", "docx", "pdf"],
        label_visibility="collapsed",
        help="Supported: TXT, DOCX, PDF",
    )
    if uploaded_resume is not None:
        try:
            extracted = extract_resume_text_from_uploaded_file(uploaded_resume)
            st.session_state.resume_text = extracted
            st.session_state.uploaded_resume_name = uploaded_resume.name
            st.success(f"Loaded: {uploaded_resume.name}")
        except Exception as e:
            st.error(f"Failed to read file: {e}")

    st.text_area(
        "Resume text",
        height=260,
        placeholder="Or paste your resume text here...",
        key="resume_text",
        label_visibility="collapsed",
    )

with col_jd:
    st.markdown('<div class="section-header">Job Description</div>', unsafe_allow_html=True)

    st.text_input(
        "JD URL",
        placeholder="Paste job posting URL (e.g. https://company.com/jobs/role)",
        key="jd_url",
        label_visibility="collapsed",
    )
    st.text_area(
        "JD text",
        height=220,
        placeholder="Or paste the full job description here...",
        key="jd_text",
        label_visibility="collapsed",
    )
    st.checkbox(
        "Strict preserve mode — keep rewrites closer to original wording",
        key="strict_preserve_mode",
    )

st.divider()

# ── Optimize button ──────────────────────────────────────────────────────────
run_button = st.button("Optimize Resume →", type="primary", use_container_width=True)

if run_button:
    if not st.session_state.resume_text.strip():
        st.error("Please upload or paste your resume.")
    elif not st.session_state.jd_text.strip() and not st.session_state.jd_url.strip():
        st.error("Please provide a job description URL or paste the JD text.")
    else:
        with st.spinner("Analyzing your resume and tailoring it to the JD..."):
            try:
                resolved_jd = resolve_jd_input(
                    jd_text=st.session_state.jd_text,
                    jd_url=st.session_state.jd_url,
                )
                st.session_state.resolved_jd_text = resolved_jd

                result = run_resume_optimization(
                    resume_text=st.session_state.resume_text,
                    jd_text=resolved_jd,
                    selected_indices=None,
                    strict_preserve_mode=st.session_state.strict_preserve_mode,
                )
                st.session_state.result = result
                st.session_state.selected_indices = list(range(len(result["optimized"])))
                st.session_state.pipeline_ran = True
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")


# ── Results ──────────────────────────────────────────────────────────────────
if st.session_state.pipeline_ran and st.session_state.result is not None:
    result = st.session_state.result
    optimized = result["optimized"]
    parsed_jd = result["parsed_jd"]
    change_log = result["change_log"]
    final_resume = result["final_resume"]

    applied_count = sum(1 for item in change_log if item["applied"])
    total_skills = len(getattr(parsed_jd, "required_skills", []))
    matched_skills = len([s for s in getattr(result["alignment"], "matched_skills", []) if s.matched])

    # Match score: simple ratio of matched skills
    match_pct = int((matched_skills / total_skills * 100)) if total_skills > 0 else 0
    score_class = "green" if match_pct >= 70 else "amber"

    # ── Metric cards ────────────────────────────────────────────────────────
    st.markdown("### Results")
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Match Score</div>
            <div class="metric-value {score_class}">{match_pct}%</div>
        </div>""", unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Suggestions Applied</div>
            <div class="metric-value">{applied_count} / {len(optimized)}</div>
        </div>""", unsafe_allow_html=True)
    with m3:
        skill_class = "green" if matched_skills == total_skills else "amber"
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Skills Matched</div>
            <div class="metric-value {skill_class}">{matched_skills} / {total_skills}</div>
        </div>""", unsafe_allow_html=True)

    st.write("")

    # ── Tabs ─────────────────────────────────────────────────────────────────
    tab_summary, tab_bullets, tab_jd, tab_final = st.tabs([
        "Summary Rewrite",
        "Bullet Suggestions",
        "JD Requirements",
        "Final Resume",
    ])

    # ── Tab 1: Summary compare ───────────────────────────────────────────────
    with tab_summary:
        original_summary = result.get("original_summary", "") or final_resume.get("summary", "")
        tailored_summary = result.get("tailored_summary", "") or final_resume.get("summary", "")

        c1, c2 = st.columns(2, gap="medium")
        with c1:
            st.markdown(f"""
            <div class="compare-box">
                <div class="compare-label">Original</div>
                {original_summary or "<em>No summary found.</em>"}
            </div>""", unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
            <div class="compare-box">
                <div class="compare-label">Tailored for this JD <span class="badge-new">NEW</span></div>
                {tailored_summary or "<em>No tailored summary generated.</em>"}
            </div>""", unsafe_allow_html=True)

    # ── Tab 2: Bullet suggestions ────────────────────────────────────────────
    with tab_bullets:
        if not optimized:
            st.info("No rewrite suggestions were generated.")
        else:
            temp_selected = list(st.session_state.selected_indices)

            for i, item in enumerate(optimized):
                checked = st.checkbox(
                    "Apply this suggestion",
                    value=(i in st.session_state.selected_indices),
                    key=f"rewrite_{i}",
                )

                st.markdown(f"""
                <div class="bullet-card">
                    <div class="skill-tag">{item['skill']}</div>
                    <div class="bullet-orig">{item['original']}</div>
                    <div class="bullet-new">{item['rewritten']}</div>
                    <div class="bullet-reason">{item['reason']}</div>
                </div>""", unsafe_allow_html=True)

                if checked and i not in temp_selected:
                    temp_selected.append(i)
                elif not checked and i in temp_selected:
                    temp_selected.remove(i)

            if sorted(temp_selected) != sorted(st.session_state.selected_indices):
                st.session_state.selected_indices = temp_selected
                updated = run_resume_optimization(
                    resume_text=st.session_state.resume_text,
                    jd_text=st.session_state.resolved_jd_text,
                    selected_indices=temp_selected,
                    strict_preserve_mode=st.session_state.strict_preserve_mode,
                )
                st.session_state.result = updated
                st.rerun()

    # ── Tab 3: JD Requirements ───────────────────────────────────────────────
    with tab_jd:
        jd_col1, jd_col2 = st.columns(2, gap="large")

        with jd_col1:
            if getattr(parsed_jd, "job_title", ""):
                st.markdown(f"**{parsed_jd.job_title}**" + (f" · {parsed_jd.company}" if getattr(parsed_jd, "company", "") else ""))

            st.markdown("**Required Skills**")
            required_skills = getattr(parsed_jd, "required_skills", [])
            if required_skills:
                for skill in required_skills:
                    matched = any(
                        s.skill == skill and s.matched
                        for s in getattr(result["alignment"], "matched_skills", [])
                    )
                    icon = "✅" if matched else "⚠️"
                    st.write(f"{icon} {skill}")
            else:
                st.caption("No required skills found.")

        with jd_col2:
            st.markdown("**Responsibilities**")
            responsibilities = getattr(parsed_jd, "responsibilities", [])
            if responsibilities:
                for r in responsibilities:
                    st.write(f"- {r}")
            else:
                st.caption("No responsibilities found.")

            preferred = getattr(parsed_jd, "preferred_skills", [])
            if preferred:
                st.markdown("**Preferred Skills**")
                for p in preferred:
                    st.write(f"- {p}")

    # ── Tab 4: Final Resume ──────────────────────────────────────────────────
    with tab_final:
        st.caption(f"{applied_count} suggestion(s) applied · Summary tailored to JD")

        if final_resume.get("name"):
            st.markdown(f"# {final_resume['name']}")

        for item in final_resume.get("contact_info", []):
            st.write(item)

        st.markdown("## Summary")
        st.write(final_resume.get("summary", "") or "_No summary_")

        st.markdown("## Skills")
        skills_dict = final_resume.get("skills", {})
        if skills_dict:
            for k, v in skills_dict.items():
                st.markdown(f"**{k.replace('_', ' ').title()}:** {', '.join(v)}")
        else:
            st.caption("No skills found.")

        languages = final_resume.get("languages", [])
        if languages:
            st.markdown("## Languages")
            st.write(", ".join(languages))

        education = final_resume.get("education", [])
        if education:
            st.markdown("## Education")
            for item in education:
                st.write(f"- {item}")

        st.markdown("## Experience")
        for exp in final_resume.get("experience", []):
            header_parts = [exp.get("company", ""), exp.get("location", ""), exp.get("title", "")]
            header = " — ".join([x for x in header_parts if x])
            dates = exp.get("dates", "")
            if dates:
                header = f"{header} ({dates})" if header else f"({dates})"
            st.markdown(f"### {header}")
            for bullet in exp.get("bullets", []):
                st.write(f"- {bullet}")

        projects = final_resume.get("projects", [])
        if projects:
            st.markdown("## Projects")
            for proj in projects:
                if proj.get("name"):
                    st.markdown(f"### {proj['name']}")
                for desc in proj.get("description", []):
                    st.write(f"- {desc}")

        for section in extra_sections_for_render(final_resume):
            title = section.get("original_title") or section.get("canonical_label") or "Other"
            st.markdown(f"## {title}")
            for item in section.get("content", []):
                st.write(f"- {item}")

        st.divider()
        st.markdown("**Download**")
        dl1, dl2, dl3 = st.columns(3)
        with dl1:
            docx_bytes = build_docx_bytes(final_resume)
            st.download_button(
                "Download DOCX",
                data=docx_bytes,
                file_name="optimized_resume.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )
        with dl2:
            st.download_button(
                "Download TXT",
                data=result["final_resume_text"],
                file_name="optimized_resume.txt",
                mime="text/plain",
                use_container_width=True,
            )
        with dl3:
            st.download_button(
                "Download Markdown",
                data=result["final_resume_markdown"],
                file_name="optimized_resume.md",
                mime="text/markdown",
                use_container_width=True,
            )

else:
    st.info("Upload your resume and provide a job description above, then click **Optimize Resume →**")
