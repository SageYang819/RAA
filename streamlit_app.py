import streamlit as st

from app.services import run_resume_optimization, extra_sections_for_render
from app.file_extractors import extract_resume_text_from_uploaded_file
from app.jd_extractors import resolve_jd_input
from app.docx_exporter import build_docx_bytes


st.set_page_config(page_title="AI Resume Alignment Agent", layout="wide")

st.title("AI Resume Alignment Agent")
st.caption("Upload a resume, provide a job description, review suggested rewrites, and generate a final tailored resume.")


def format_experience(experience_list):
    lines = []
    for exp in experience_list:
        header_parts = [
            exp.get("company", ""),
            exp.get("location", ""),
            exp.get("title", ""),
        ]
        header = " — ".join([x for x in header_parts if x])
        dates = exp.get("dates", "")
        if dates:
            header = f"{header} ({dates})" if header else f"({dates})"

        lines.append(f"### {header}")
        for bullet in exp.get("bullets", []):
            lines.append(f"- {bullet}")
        lines.append("")
    return "\n".join(lines)


defaults = {
    "resume_text": "",
    "jd_text": "",
    "jd_url": "",
    "resolved_jd_text": "",
    "pipeline_ran": False,
    "result": None,
    "selected_indices": [],
    "uploaded_resume_name": "",
    "strict_preserve_mode": True,
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


def reset_app():
    st.session_state.resume_text = ""
    st.session_state.jd_text = ""
    st.session_state.jd_url = ""
    st.session_state.resolved_jd_text = ""
    st.session_state.pipeline_ran = False
    st.session_state.result = None
    st.session_state.selected_indices = []
    st.session_state.uploaded_resume_name = ""
    st.session_state.strict_preserve_mode = True


st.sidebar.header("Input")

uploaded_resume = st.sidebar.file_uploader(
    "Upload Resume File",
    type=["txt", "docx", "pdf"],
    help="Supported formats: TXT, DOCX, PDF",
)

if uploaded_resume is not None:
    try:
        extracted_resume_text = extract_resume_text_from_uploaded_file(uploaded_resume)
        st.session_state.resume_text = extracted_resume_text
        st.session_state.uploaded_resume_name = uploaded_resume.name
        st.sidebar.success(f"Loaded: {uploaded_resume.name}")
    except Exception as e:
        st.sidebar.error(f"Failed to read file: {e}")

st.sidebar.text_area(
    "Resume Text",
    height=220,
    placeholder="Upload a resume file or paste the full resume text here...",
    key="resume_text",
)

st.sidebar.markdown("---")

st.sidebar.text_input(
    "Job Description Link",
    placeholder="Paste a job posting URL here...",
    key="jd_url",
)

st.sidebar.text_area(
    "Job Description Text",
    height=220,
    placeholder="Paste the full job description here as a fallback...",
    key="jd_text",
)

st.sidebar.checkbox(
    "Strict preserve mode",
    help="Keep rewrites closer to the original wording.",
    key="strict_preserve_mode",
)

col_btn1, col_btn2 = st.sidebar.columns(2)
run_button = col_btn1.button("Optimize Resume", type="primary")
reset_button = col_btn2.button("Reset")

if reset_button:
    reset_app()
    st.rerun()


if run_button:
    if not st.session_state.resume_text.strip():
        st.error("Please provide resume text or upload a resume file.")
    elif not st.session_state.jd_text.strip() and not st.session_state.jd_url.strip():
        st.error("Please provide a JD link or paste JD text.")
    else:
        with st.spinner("Running resume optimization pipeline..."):
            try:
                resolved_jd_text = resolve_jd_input(
                    jd_text=st.session_state.jd_text,
                    jd_url=st.session_state.jd_url,
                )
                st.session_state.resolved_jd_text = resolved_jd_text

                result = run_resume_optimization(
                    resume_text=st.session_state.resume_text,
                    jd_text=resolved_jd_text,
                    selected_indices=None,
                    strict_preserve_mode=st.session_state.strict_preserve_mode,
                )

                st.session_state.result = result
                st.session_state.selected_indices = list(range(len(result["optimized"])))
                st.session_state.pipeline_ran = True
                st.rerun()

            except Exception as e:
                st.error(f"Error: {e}")


if st.session_state.pipeline_ran and st.session_state.result is not None:
    result = st.session_state.result
    parsed_jd = result["parsed_jd"]
    optimized = result["optimized"]

    tab1, tab2, tab3 = st.tabs([
        "JD Requirements",
        "Suggested Rewrites",
        "Final Resume",
    ])

    with tab1:
        st.subheader("What the JD Requires")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Basic Information")
            if getattr(parsed_jd, "job_title", ""):
                st.write(f"**Job Title:** {parsed_jd.job_title}")
            if getattr(parsed_jd, "company", ""):
                st.write(f"**Company:** {parsed_jd.company}")

            st.markdown("### Required Skills")
            required_skills = getattr(parsed_jd, "required_skills", [])
            if required_skills:
                for skill in required_skills:
                    st.write(f"- {skill}")
            else:
                st.write("_No required skills found._")

        with col2:
            st.markdown("### Responsibilities")
            responsibilities = getattr(parsed_jd, "responsibilities", [])
            if responsibilities:
                for item in responsibilities:
                    st.write(f"- {item}")
            else:
                st.write("_No responsibilities found._")

            st.markdown("### Preferred Skills")
            preferred_skills = getattr(parsed_jd, "preferred_skills", [])
            if preferred_skills:
                for item in preferred_skills:
                    st.write(f"- {item}")
            else:
                st.write("_No preferred skills found._")

    with tab2:
        st.subheader("Suggested Rewrites")

        if not optimized:
            st.info("No safe rewrite suggestions were generated.")
        else:
            temp_selected = []

            for i, item in enumerate(optimized):
                with st.container():
                    st.markdown(f"### Suggestion {i + 1}")
                    st.markdown(f"**Target JD Requirement:** {item['skill']}")

                    st.markdown("**Original**")
                    st.write(item["original"])

                    st.markdown("**Suggested Rewrite**")
                    st.write(item["rewritten"])

                    st.markdown("**Reason**")
                    st.caption(item["reason"])

                    apply_this = st.checkbox(
                        f"Apply Suggestion {i + 1}",
                        value=(i in st.session_state.selected_indices),
                        key=f"rewrite_{i}",
                    )

                    if apply_this:
                        temp_selected.append(i)

                    st.divider()

            if temp_selected != st.session_state.selected_indices:
                st.session_state.selected_indices = temp_selected

                updated_result = run_resume_optimization(
                    resume_text=st.session_state.resume_text,
                    jd_text=st.session_state.resolved_jd_text,
                    selected_indices=st.session_state.selected_indices,
                    strict_preserve_mode=st.session_state.strict_preserve_mode,
                )
                st.session_state.result = updated_result

        st.markdown("---")
        st.subheader("Change Log")

        change_log = st.session_state.result["change_log"]
        if not change_log:
            st.info("No changes to display.")
        else:
            for idx, item in enumerate(change_log, start=1):
                status = "Applied" if item["applied"] else "Not Applied"

                with st.container():
                    st.markdown(f"### Change {idx} · {status}")
                    st.markdown(f"**Target JD Requirement:** {item['target_requirement']}")

                    st.markdown("**Original**")
                    st.write(item["original"])

                    st.markdown("**Rewritten**")
                    st.write(item["rewritten"])

                    st.markdown("**Reason**")
                    st.caption(item["reason"])

                    st.divider()

    with tab3:
        final_resume = st.session_state.result["final_resume"]
        applied_count = sum(1 for item in st.session_state.result["change_log"] if item["applied"])

        st.subheader("Final Resume Based on Selected Suggestions")
        st.caption(f"{applied_count} suggestion(s) currently applied.")

        if final_resume.get("name"):
            st.markdown(f"# {final_resume['name']}")

        contact_info = final_resume.get("contact_info", [])
        if contact_info:
            for item in contact_info:
                st.write(item)

        st.markdown("## Summary")
        st.write(final_resume.get("summary", "") or "_No summary found_")

        st.markdown("## Skills")
        skills_dict = final_resume.get("skills", {})
        if skills_dict:
            for k, v in skills_dict.items():
                st.markdown(f"**{k.replace('_', ' ').title()}**: {', '.join(v)}")
        else:
            st.write("_No skills found_")

        st.markdown("## Languages")
        languages = final_resume.get("languages", [])
        if languages:
            st.write(", ".join(languages))
        else:
            st.write("_No languages found_")

        st.markdown("## Education")
        education = final_resume.get("education", [])
        if education:
            for item in education:
                st.write(f"- {item}")
        else:
            st.write("_No education found_")

        st.markdown("## Experience")
        st.markdown(format_experience(final_resume.get("experience", [])))

        projects = final_resume.get("projects", [])
        if projects:
            st.markdown("## Projects")
            for proj in projects:
                if proj.get("name"):
                    st.markdown(f"### {proj['name']}")
                for desc in proj.get("description", []):
                    st.write(f"- {desc}")

        extra_sections = extra_sections_for_render(final_resume)
        for section in extra_sections:
            title = section.get("original_title") or section.get("canonical_label") or "Other"
            st.markdown(f"## {title}")
            for item in section.get("content", []):
                st.write(f"- {item}")

        st.markdown("---")
        st.subheader("Download")

        docx_bytes = build_docx_bytes(final_resume)

        st.download_button(
            label="Download as DOCX",
            data=docx_bytes,
            file_name="optimized_resume.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

        st.download_button(
            label="Download as TXT",
            data=st.session_state.result["final_resume_text"],
            file_name="optimized_resume.txt",
            mime="text/plain",
        )

        st.download_button(
            label="Download as Markdown",
            data=st.session_state.result["final_resume_markdown"],
            file_name="optimized_resume.md",
            mime="text/markdown",
        )

else:
    st.info(
        "Upload a resume file or paste resume text in the left sidebar, then provide a JD link or JD text and click 'Optimize Resume'."
    )