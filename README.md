# Tailor — resume & cover-letter helper

Paste a job description, choose **resume** and/or **cover letter**, and generate tailored output from:

1. **Experience bank** (`data/experience_bank.yaml`) — roles, bullets, skills, and flag metadata (source of truth)
2. **Personal background** (`data/background.md`) — voice/context for cover letters
3. **LaTeX resume template** (`data/resume_template.tex`) — sb2nov-style; fill this structure; keep custom macros

The model may **select and rephrase** facts from those sources. It must **never invent** employers, titles, dates, or metrics.

**v1 artifact is `.tex`** (plus cover-letter Markdown). PDF compilation is optional/out of scope for v1 — compile locally with your usual TeX setup, or add a TeX Live step later.

---

## Quick start (Docker Compose)

```bash
# 1. API key
cp .env.example .env
# Edit .env — set either OPENAI_API_KEY or ANTHROPIC_API_KEY

# 2. Run
docker compose up --build

# 3. Open
# http://localhost:8000
```

Paste a JD, keep both checkboxes on, click **Generate**. Outputs appear in the UI and under `data/output/` (`resume-*.tex`, `cover-letter-*.md`).

Stop with `Ctrl+C`, or `docker compose down`.

---

## Local run (without Docker)

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # add OPENAI_API_KEY or ANTHROPIC_API_KEY
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open http://localhost:8000

---

## LLM configuration

Set **one** provider in `.env` (see `.env.example`):

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | OpenAI or any OpenAI-compatible endpoint |
| `OPENAI_BASE_URL` | Default `https://api.openai.com/v1` |
| `OPENAI_MODEL` | Default `gpt-4o-mini` |
| `ANTHROPIC_API_KEY` | Anthropic Messages API |
| `ANTHROPIC_MODEL` | Default `claude-sonnet-4-20250514` |

If both keys are set, **OpenAI-compatible wins**.

---

## Where to put your real files

Seeded from your sb2nov resume. Edit these as needed:

| Path | What it is |
|------|------------|
| `data/experience_bank.yaml` | **Your** roles, bullets, skills, and CHECK/TODO/pre-launch flags |
| `data/background.md` | Voice, career story, letter constraints |
| `data/resume_template.tex` | sb2nov LaTeX skeleton (preamble + macros preserved) |
| `data/output/` | Generated `resume-*.tex` and `cover-letter-*.md` |

`./data` is bind-mounted into the container, so edits on the host show up immediately and outputs persist after the container stops.

---

## Bullet flags (read before sending)

The bank encodes comments from the original `.tex` as metadata. Prompts prefer conservative wording; **you still own the final send**.

| Flag | Meaning |
|------|---------|
| `public_safe` | Preferred default for applications |
| `check` | Needs your confirmation (product names, stage counts, etc.) |
| `todo` | Incomplete — don’t invent the missing outcome |
| `pre_launch` | Safer pre-GA wording; prefer when launch claims are uncertain |
| `send_after_ga` | Do not use until the named products are GA / public |

Notable open items from the source resume:

- IBM release / AI agent bullets — confirm public names; prefer pre-launch alternates until CCM 6.4.3 and the AI agent are GA
- OIDC / roadmap TODOs — don’t claim delivery outcomes not in the bank
- Tesla pipeline — confirm six- vs seven-stage before sending

---

## Repo layout

```
app/                 FastAPI app, HTML/CSS
  main.py            Routes + UI
  tailor.py          Prompts + file I/O
  llm.py             OpenAI-compatible / Anthropic client
  config.py          Settings from env
data/
  experience_bank.yaml
  background.md
  resume_template.tex
  output/            Generated files (gitignored contents)
Dockerfile
docker-compose.yml
.env.example
requirements.txt
```

Custom LaTeX commands kept in the template: `\resumeItem`, `\resumeSubheading`, `\resumeProjectHeading`, `\resumeSubHeadingListStart` / `End`, `\resumeItemListStart` / `End`, etc.

---

## What you’re learning (Docker)

| Concept | In this project |
|---------|-----------------|
| **Image** | Built from the `Dockerfile` — Python + app code + deps. Immutable recipe. |
| **Container** | A running instance of that image (`docker compose up`). |
| **Volume / bind mount** | `./data:/app/data` maps your host `data/` folder into the container so bank/template/outputs stay on disk. |
| **Compose** | `docker-compose.yml` wires the `app` service, port `8000`, `env_file: .env`, and the data mount in one command. |

---

## Health check

```bash
curl http://localhost:8000/health
```

---

## Honesty rule

Prompts instruct the model: only use facts from the experience bank and background; respect CHECK/TODO/pre-launch flags; tailor wording and selection; never fabricate. Still review every output before you send it.
