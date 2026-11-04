"""Load source files and ask the LLM to tailor resume / cover letter."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import yaml

from app.config import Settings
from app.llm import complete
from app.mock_fill import build_mock_cover_letter, build_mock_resume

HONESTY = """
HONESTY RULE (non-negotiable):
- Use ONLY facts present in the experience bank and personal background.
- You may select, reorder, lightly rephrase, and emphasize — never invent.
- Do NOT fabricate employers, job titles, dates, metrics, tools, certifications,
  team sizes, revenue, awards, or degrees.
- Respect bullet flags in the bank:
  - Prefer public_safe wording by default.
  - If a bullet has check / todo / send_after_ga, prefer its pre_launch alternate
    when present, or omit contested claims / unfinished outcomes.
  - Never invent delivery outcomes for TODO items.
  - Never use send_after_ga claims as if products are already GA.
- If the job asks for something not supported by the sources, omit it or note
  adjacent real experience honestly. Never pad with plausible fiction.
""".strip()


def load_sources(settings: Settings) -> dict[str, str]:
    bank = settings.experience_bank_path.read_text(encoding="utf-8")
    background = settings.background_path.read_text(encoding="utf-8")
    template = settings.resume_template_path.read_text(encoding="utf-8")
    # Validate YAML early so we fail clearly if the bank is broken.
    yaml.safe_load(bank)
    return {"bank": bank, "background": background, "template": template}


async def generate_resume(settings: Settings, job_description: str, sources: dict[str, str]) -> str:
    if settings.mock_llm:
        return build_mock_resume(settings)

    system = f"""You are a careful resume editor for a real person.
{HONESTY}

Fill the provided LaTeX resume template (sb2nov-style).
HARD RULES FOR LATEX:
- Keep the entire preamble, \\documentclass, packages, margin tweaks, and custom
  commands (\\resumeItem, \\resumeSubheading, \\resumeProjectHeading,
  \\resumeSubHeadingListStart/End, \\resumeItemListStart/End, etc.) unchanged.
- Keep the heading/contact block and Education facts exact unless the bank differs.
- Emit tailored Experience using those macros only — do not invent a new layout.
- Use \\textbf{{...}} sparingly for emphasis, matching the template style.
- Return ONLY a complete compilable .tex document. No markdown fences, no commentary.
""".strip()

    user = f"""## Job description
{job_description}

## Experience bank (source of truth; includes flags and alternate bullets)
{sources["bank"]}

## LaTeX template to fill (preserve structure and macros)
{sources["template"]}
"""
    return await complete(settings, system, user)


async def generate_cover_letter(
    settings: Settings, job_description: str, sources: dict[str, str]
) -> str:
    if settings.mock_llm:
        return build_mock_cover_letter(settings, job_description)

    system = f"""You are a careful cover-letter writer for a real person.
{HONESTY}

Write in the voice described in the personal background.
Return ONLY Markdown (no LaTeX, no code fences). Aim for ~250–400 words."""

    user = f"""## Job description
{job_description}

## Experience bank (facts only; respect flags)
{sources["bank"]}

## Personal background (voice & context)
{sources["background"]}
"""
    return await complete(settings, system, user)


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def save_outputs(
    settings: Settings,
    *,
    resume_tex: str | None,
    cover_md: str | None,
) -> dict[str, str]:
    out_dir: Path = settings.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = _stamp()
    paths: dict[str, str] = {}

    if resume_tex is not None:
        path = out_dir / f"resume-{stamp}.tex"
        cleaned = _strip_fences(resume_tex)
        path.write_text(cleaned + ("\n" if not cleaned.endswith("\n") else ""), encoding="utf-8")
        paths["resume"] = str(path.relative_to(settings.data_dir.parent))

    if cover_md is not None:
        path = out_dir / f"cover-letter-{stamp}.md"
        cleaned = _strip_fences(cover_md)
        path.write_text(cleaned + ("\n" if not cleaned.endswith("\n") else ""), encoding="utf-8")
        paths["cover_letter"] = str(path.relative_to(settings.data_dir.parent))

    return paths


def _strip_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        lines = t.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        t = "\n".join(lines).strip()
    return t
