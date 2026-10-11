from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.llm import LLMError
from app.tailor import generate_cover_letter, generate_resume, load_sources, save_outputs

APP_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Resume Tailorer", version="1.0.0")
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    provider = settings.provider() or "none"
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "provider": provider,
            "model": (
                settings.openai_model
                if provider == "openai"
                else settings.anthropic_model
                if provider == "anthropic"
                else "bank-fill"
                if provider == "mock"
                else "—"
            ),
        },
    )


@app.get("/health")
async def health() -> dict:
    return {
        "ok": True,
        "provider": settings.provider(),
        "data_dir": str(settings.data_dir),
        "bank_exists": settings.experience_bank_path.exists(),
        "background_exists": settings.background_path.exists(),
        "template_exists": settings.resume_template_path.exists(),
    }


@app.post("/api/generate")
async def api_generate(
    job_description: str = Form(...),
    want_resume: bool = Form(False),
    want_cover: bool = Form(False),
) -> JSONResponse:
    jd = (job_description or "").strip()
    if len(jd) < 40:
        raise HTTPException(
            status_code=400,
            detail="Paste a fuller job description (at least ~40 characters).",
        )
    if not want_resume and not want_cover:
        raise HTTPException(status_code=400, detail="Choose resume and/or cover letter.")

    try:
        sources = load_sources(settings)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=f"Missing data file: {exc.filename}") from exc
    except Exception as exc:  # noqa: BLE001 — surface YAML/load errors cleanly
        raise HTTPException(status_code=500, detail=f"Failed to load source data: {exc}") from exc

    resume_tex: str | None = None
    cover_md: str | None = None

    try:
        if want_resume:
            resume_tex = await generate_resume(settings, jd, sources)
        if want_cover:
            cover_md = await generate_cover_letter(settings, jd, sources)
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    paths = save_outputs(settings, resume_tex=resume_tex, cover_md=cover_md)

    return JSONResponse(
        {
            "ok": True,
            "paths": paths,
            "resume": resume_tex,
            "cover_letter": cover_md,
        }
    )


@app.get("/download/{kind}/{filename}")
async def download(kind: str, filename: str) -> FileResponse:
    if kind not in {"resume", "cover"}:
        raise HTTPException(status_code=404, detail="Unknown kind")
    safe = Path(filename).name
    if safe != filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    path = settings.output_dir / safe
    if not path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    if safe.endswith(".tex"):
        media = "application/x-tex"
    elif safe.endswith(".md"):
        media = "text/markdown"
    else:
        media = "application/octet-stream"
    return FileResponse(path, media_type=media, filename=safe)
