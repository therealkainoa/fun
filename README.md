# Tailor — resume & cover-letter helper

Paste a job description, choose **resume** and/or **cover letter**, and generate tailored output from:

1. **Experience bank** (`data/experience_bank.yaml`) — roles, bullets, skills, and flag metadata (source of truth)
2. **Personal background** (`data/background.md`) — voice/context for cover letters
3. **LaTeX resume template** (`data/resume_template.tex`) — sb2nov-style; fill this structure; keep custom macros

The model may **select and rephrase** facts from those sources. It must **never invent** employers, titles, dates, or metrics.

Outputs: tailored **`.tex`**, compiled **PDF** (via Compose `tex` service), and cover-letter **Markdown**.

---

## Quick start (Docker Compose)

```bash
# 1. API key (or MOCK_LLM=1 for offline)
cp .env.example .env
# Edit .env — set OPENAI_API_KEY or ANTHROPIC_API_KEY, or MOCK_LLM=1

# 2. Build & run both services (app + tex)
docker compose up --build

# 3. Open
# http://localhost:8000
```

Paste a JD and generate. The results panel **defaults to an embedded PDF preview**; toggle to **LaTeX source** (editable) and use **Save & recompile PDF** after tweaks. Download PDF / `.tex` stay available. Files land under `data/output/` (`resume-*.tex`, `resume-*.pdf`, `cover-letter-*.md`).

**Pull / rebuild after updates:**

```bash
git pull
docker compose up --build
```

Stop with `Ctrl+C`, or `docker compose down`.

---

## PDF compile (Compose `tex` service)

| Piece | Role |
|-------|------|
| `app` | FastAPI UI; writes `.tex` into the shared `./data` mount; asks `tex` to compile |
| `tex` | TeX Live + `latexmk` sidecar (`Dockerfile.tex`); HTTP compile API on port **8080** |
| `./data` bind mount | Shared by both services — `app` sees `/app/data`, `tex` sees `/data` |

Flow: generate resume → save `data/output/resume-….tex` → `app` POSTs to `TEX_COMPILE_URL` → `latexmk -pdf` → `data/output/resume-….pdf`.

`TEX_COMPILE_URL` defaults to `http://host.docker.internal:8080/compile` (Compose `extra_hosts` + published `8080`). On a typical Docker install you can switch it to `http://tex:8080/compile` (Compose DNS). Either way you learn: **two services, one shared volume, one compile API**.

### Image size tradeoff

`Dockerfile.tex` installs a **focused** Debian TeX set (`texlive-latex-base/recommended/extra` + recommended fonts + `latexmk`), not `texlive-full` and not `texlive-fonts-extra`. Measured here: **`tex` ≈ 991MB**, **`app` ≈ 254MB**. A full TeX Live image is multi‑GB.

---

## Local run (without Docker)

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open http://localhost:8000

Without Compose, `TEX_COMPILE_URL` is empty → **`.tex` only** (no PDF). To get PDFs locally, either use Compose or point `TEX_COMPILE_URL` at a running compile sidecar.

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
| `MOCK_LLM` | `1` = offline bank-fill (no API key) |
| `TEX_COMPILE_URL` | Set by Compose to `http://tex:8080/compile` |

If both LLM keys are set, **OpenAI-compatible wins**.

### Offline demo (no API key)

```bash
# in .env
MOCK_LLM=1
docker compose up --build
```

---

## Where to put your real files

| Path | What it is |
|------|------------|
| `data/experience_bank.yaml` | **Your** roles, bullets, skills, and CHECK/TODO/pre-launch flags |
| `data/background.md` | Voice, career story, letter constraints |
| `data/resume_template.tex` | sb2nov LaTeX skeleton (preamble + macros preserved) |
| `data/output/` | Generated `resume-*.tex`, `resume-*.pdf`, `cover-letter-*.md` |

---

## Bullet flags (read before sending)

| Flag | Meaning |
|------|---------|
| `public_safe` | Preferred default for applications |
| `check` | Needs your confirmation (product names, stage counts, etc.) |
| `todo` | Incomplete — don’t invent the missing outcome |
| `pre_launch` | Safer pre-GA wording; prefer when launch claims are uncertain |
| `send_after_ga` | Do not use until the named products are GA / public |

Notable open items: IBM release / AI agent public names; OIDC TODO outcomes; Tesla six- vs seven-stage.

---

## Repo layout

```
app/                 FastAPI app, HTML/CSS
  main.py            Routes + UI
  tailor.py          Prompts + file I/O
  pdf.py             Calls the tex sidecar
  llm.py             OpenAI-compatible / Anthropic client
  config.py          Settings from env
tex_service/
  compile_server.py  Tiny HTTP wrapper around latexmk
data/
  experience_bank.yaml
  background.md
  resume_template.tex
  output/
Dockerfile           Python app image
Dockerfile.tex       TeX Live sidecar image
docker-compose.yml   app + tex, shared ./data mount
.env.example
requirements.txt
```

---

## What you’re learning (Docker)

| Concept | In this project |
|---------|-----------------|
| **Image** | Two recipes: `Dockerfile` (Python app) and `Dockerfile.tex` (TeX sidecar). |
| **Container** | Running instances of those images (`docker compose up`). |
| **Volume / bind mount** | `./data` mounted into **both** services so `.tex` written by `app` is visible to `tex`, and the PDF lands back on the host. |
| **Compose** | Wires `app` + `tex`, env, depends_on, and internal DNS (`http://tex:8080`) in one command. |

---

## Health check

```bash
curl http://localhost:8000/health
docker compose exec tex python3 -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8080/health').read().decode())"
```

---

## Honesty rule

Prompts instruct the model: only use facts from the experience bank and background; respect CHECK/TODO/pre-launch flags; tailor wording and selection; never fabricate. Still review every output before you send it.
