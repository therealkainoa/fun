"""Ask the Compose `tex` sidecar to compile a .tex file to PDF."""

from __future__ import annotations

from pathlib import Path

import httpx

from app.config import Settings


class PDFError(RuntimeError):
    pass


async def compile_resume_pdf(settings: Settings, resume_rel_path: str) -> str:
    """Compile `data/output/resume-….tex` via TEX_COMPILE_URL.

    Returns repo-relative PDF path (e.g. data/output/resume-….pdf).
    """
    url = (settings.tex_compile_url or "").rstrip("/")
    if not url:
        raise PDFError(
            "PDF compile not configured. Set TEX_COMPILE_URL (Compose sets "
            "http://tex:8080/compile)."
        )

    # Normalize to something the tex service understands.
    rel = resume_rel_path.removeprefix("./")
    payload = {"tex": rel}

    async with httpx.AsyncClient(timeout=150.0) as client:
        try:
            resp = await client.post(url, json=payload)
        except httpx.RequestError as exc:
            raise PDFError(
                f"Could not reach TeX service at {url}: {exc}. "
                "Is the `tex` service up? Try: docker compose up --build"
            ) from exc

    try:
        data = resp.json()
    except Exception as exc:  # noqa: BLE001
        raise PDFError(f"TeX service returned non-JSON ({resp.status_code}): {resp.text[:500]}") from exc

    if resp.status_code >= 400 or not data.get("ok"):
        raise PDFError(data.get("error") or f"TeX compile failed ({resp.status_code})")

    pdf = data.get("pdf")
    if not pdf:
        raise PDFError("TeX service response missing pdf path")

    # Confirm the file landed on the shared volume.
    pdf_path = Path(pdf)
    if not pdf_path.is_absolute():
        pdf_path = settings.data_dir.parent / pdf
    if not pdf_path.is_file():
        # Also try under data_dir/output
        alt = settings.output_dir / Path(pdf).name
        if alt.is_file():
            return str(alt.relative_to(settings.data_dir.parent))
        raise PDFError(f"PDF reported but missing on disk: {pdf}")

    return str(Path(pdf).as_posix() if not str(pdf).startswith("data/") else pdf)
