"""Deterministic offline fill from the experience bank (MOCK_LLM=1).

Uses only bank facts. Prefers public_safe / pre_launch wording when CHECK/TODO flags apply.
"""

from __future__ import annotations

import re
from typing import Any

import yaml

from app.config import Settings


def _escape_tex(text: str) -> str:
    # Minimal escaping for common specials in resume prose.
    repl = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(repl.get(ch, ch) for ch in text)


def _pick_bullet_text(bullet: dict[str, Any]) -> str | None:
    flags = set(bullet.get("flags") or [])
    alternates = bullet.get("alternates") or []

    if "send_after_ga" in flags or "check" in flags:
        for alt in alternates:
            alt_flags = set(alt.get("flags") or [])
            if "pre_launch" in alt_flags or "public_safe" in alt_flags:
                return alt.get("text")
        if "check" in flags and "send_after_ga" not in flags:
            # Still usable if no safer alternate — include but don't invent.
            return bullet.get("text")
        if "send_after_ga" in flags:
            return None

    if "todo" in flags:
        # Safe as written for work done; just don't invent outcomes (bank already omits them).
        return bullet.get("text")

    return bullet.get("text")


def _role_block(role: dict[str, Any]) -> str:
    company = role["company"]
    location = role.get("location") or ""
    title = role["title"]
    start = role.get("start") or ""
    end = role.get("end") or ""
    dates = f"{start} -- {end}".strip(" -") if end else start

    extra = role.get("extra") or {}
    if extra.get("latex_company_line"):
        # NSF-style: company arg is the research-intern + poster link line.
        company_arg = extra["latex_company_line"]
        location_arg = dates  # matches original template layout
        title_arg = extra.get("latex_title_line") or title
        date_arg = ""
    else:
        company_arg = _escape_tex(company)
        location_arg = _escape_tex(location)
        title_arg = _escape_tex(title)
        date_arg = _escape_tex(dates)

    items: list[str] = []
    for bullet in role.get("bullets") or []:
        text = _pick_bullet_text(bullet)
        if not text:
            continue
        items.append(f"    \\resumeItem{{{_escape_tex(text.strip())}}}")

    if not items:
        return ""

    body = "\n".join(items)
    return (
        f"\\resumeSubheading\n"
        f"  {{{company_arg}}}{{{location_arg}}}\n"
        f"  {{{title_arg}}}{{{date_arg}}}\n"
        f"  \\resumeItemListStart\n"
        f"{body}\n"
        f"  \\resumeItemListEnd"
    )


def build_mock_resume(settings: Settings) -> str:
    bank = yaml.safe_load(settings.experience_bank_path.read_text(encoding="utf-8"))
    template = settings.resume_template_path.read_text(encoding="utf-8")

    role_blocks = [_role_block(r) for r in bank.get("roles") or []]
    role_blocks = [b for b in role_blocks if b]
    experience = "\n\n".join(role_blocks)

    # Drop the EXAMPLE ROLE SHAPE comment block before inserting roles.
    cleaned = re.sub(
        r"\n\s*% EXAMPLE ROLE SHAPE.*?(?=\n\s*% --- TAILOR)",
        "\n",
        template,
        count=1,
        flags=re.S,
    )

    marker = "% --- TAILOR: emit selected \\resumeSubheading blocks here ---"
    if marker not in cleaned:
        raise RuntimeError("resume_template.tex missing TAILOR marker")
    return cleaned.replace(marker, experience)


def build_mock_cover_letter(settings: Settings, job_description: str) -> str:
    bank = yaml.safe_load(settings.experience_bank_path.read_text(encoding="utf-8"))
    profile = bank.get("profile") or {}
    name = profile.get("name") or "Candidate"
    roles = bank.get("roles") or []
    ibm = next((r for r in roles if r.get("id") == "ibm-pm"), roles[0] if roles else None)
    aws = next((r for r in roles if r.get("id") == "aws-jumpstart"), None)

    jd_snip = " ".join(job_description.split())[:180]
    lines = [
        f"# Cover letter — {name}",
        "",
        f"I'm writing about the role described as: {jd_snip}…",
        "",
    ]
    if ibm:
        lines.append(
            f"At {ibm['company']}, I serve as {ibm['title']}, owning roadmap and "
            "enterprise B2B integration products with cross-functional launch work "
            "(facts from my experience bank only)."
        )
        lines.append("")
    if aws:
        lines.append(
            f"Previously at {aws['company']} ({aws['title']}), I took a developer-facing "
            "ML evaluation framework from design to launch for SageMaker JumpStart."
        )
        lines.append("")
    lines.extend(
        [
            "I'd welcome a conversation about how this background maps to your needs.",
            "",
            f"— {name}",
            "",
            "_Generated in MOCK_LLM mode (no model call)._ ",
        ]
    )
    return "\n".join(lines)
