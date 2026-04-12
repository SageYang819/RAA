# AI Resume Alignment Agent (RAA)

> Tailor your resume to any job description — without fabricating experience you don't have.

Most resume tools either generate generic polish or invent qualifications you never had. RAA takes a different approach: it realigns **what you actually did** using the language and framing of the target job, so every word stays true to your real experience.

---

## What makes RAA different

- **No fabrication** — every rewrite is grounded in your original resume. No invented tools, metrics, or responsibilities.
- **JD-aware rewriting** — bullets and summary are reframed using the job's actual language, not generic buzzwords.
- **You stay in control** — review each suggested change and choose what to apply before generating the final resume.
- **Match score + skill gap analysis** — see at a glance how well your resume aligns with the JD requirements.

---

## How it works

1. Upload your resume (`.txt`, `.docx`, `.pdf`) or paste the text
2. Paste a job posting URL or the full JD text
3. RAA extracts key requirements and responsibilities from the JD
4. It suggests targeted rewrites for your bullets and summary — based only on what's already in your resume
5. You select which suggestions to apply
6. Download your tailored resume as `.docx`, `.txt`, or `.md`

---

## Live demo

[**Try it on Streamlit →**](https://sageyang819-raa-streamlit-app.streamlit.app)

> Requires your own OpenAI API key (set as `OPENAI_API_KEY` in `.env` for local use, or in Streamlit secrets for deployment).

---

## Quick start

```bash
git clone https://github.com/SageYang819/RAA.git
cd RAA

pip install -r requirements.txt

cp .env.example .env
# Add your OpenAI API key to .env

streamlit run streamlit_app.py
```

---

## Project structure

```
RAA/
├── app/
│   ├── schemas.py          # Pydantic data models
│   ├── parsers.py          # LLM-based resume + JD parsing
│   ├── normalizers.py      # Text cleaning and section detection
│   ├── aligner.py          # Skill matching and gap analysis
│   ├── rewrite_agent.py    # Bullet + summary rewriting (core AI logic)
│   ├── services.py         # Main pipeline orchestration
│   ├── file_extractors.py  # PDF / DOCX / TXT extraction
│   ├── jd_extractors.py    # JD URL scraping + text handling
│   └── docx_exporter.py    # Final resume export to .docx
├── streamlit_app.py        # UI
├── requirements.txt
├── .env.example
└── README.md
```

---

## Tech stack

- **Frontend**: Streamlit
- **AI**: OpenAI GPT-4o-mini (parsing, alignment, rewriting)
- **Resume parsing**: pdfplumber, python-docx
- **Export**: python-docx

---

## Roadmap

- [ ] User-provided API key input in UI (no setup required)
- [ ] Cover letter generation aligned to the same JD
- [ ] Match score explanation with per-skill breakdown
- [ ] Support for multiple job applications / resume versions

---

## Contributing

PRs and issues welcome. If you find a case where RAA fabricates something it shouldn't — please open an issue with the example. Keeping rewrites honest is the core design principle of this project.

---

## License

MIT
