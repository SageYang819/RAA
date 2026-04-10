# AI Resume Alignment Agent

An AI-powered resume tailoring tool that helps users align their resume with a specific job description.

## What it does

This app allows users to:

- Upload a resume file (`.txt`, `.docx`, `.pdf`) or paste resume text
- Provide a job description through a link or pasted text
- Extract key JD requirements
- Generate safer rewrite suggestions for resume bullets
- Let users choose which suggestions to apply
- Generate a final tailored resume
- Download the final result as `.docx`, `.txt`, or `.md`

## Current product scope

This is an MVP version focused on the core workflow:

1. Resume input
2. JD input
3. Suggested rewrites
4. User selection
5. Final resume generation
6. Export

## Supported input formats

### Resume
- TXT
- DOCX
- PDF
- Pasted plain text

### Job Description
- Job posting link
- Pasted plain text

## Output formats

- DOCX
- TXT
- Markdown

## Project structure

```text
resume-agent/
├── app/
│   ├── schemas.py
│   ├── parsers.py
│   ├── normalizers.py
│   ├── aligner.py
│   ├── rewrite_agent.py
│   ├── services.py
│   ├── file_extractors.py
│   ├── jd_extractors.py
│   └── docx_exporter.py
├── streamlit_app.py
├── requirements.txt
├── README.md
├── .env.example
└── .gitignore