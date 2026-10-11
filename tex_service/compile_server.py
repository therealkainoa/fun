#!/usr/bin/env python3
"""Minimal HTTP compile sidecar for Compose.

POST /compile  JSON: {"tex": "output/resume-....tex"}  (path under DATA_DIR)
GET  /health
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

DATA_DIR = Path(os.environ.get("DATA_DIR", "/data")).resolve()
PORT = int(os.environ.get("PORT", "8080"))


def _safe_tex_path(rel: str) -> Path:
    rel = (rel or "").removeprefix("data/").lstrip("/")
    if not rel or ".." in Path(rel).parts:
        raise ValueError("invalid path")
    candidate = (DATA_DIR / rel).resolve()
    out_root = (DATA_DIR / "output").resolve()
    if out_root not in candidate.parents and candidate.parent != out_root:
        raise ValueError("tex path must be under data/output/")
    if candidate.suffix != ".tex":
        raise ValueError("only .tex files supported")
    if not candidate.is_file():
        raise FileNotFoundError(rel)
    return candidate


def compile_pdf(tex_path: Path) -> Path:
    workdir = tex_path.parent
    latexmk = shutil.which("latexmk")
    if latexmk:
        cmd = [
            latexmk,
            "-pdf",
            "-interaction=nonstopmode",
            "-halt-on-error",
            tex_path.name,
        ]
    else:
        pdflatex = shutil.which("pdflatex")
        if not pdflatex:
            raise RuntimeError("neither latexmk nor pdflatex found in PATH")
        cmd = [
            pdflatex,
            "-interaction=nonstopmode",
            "-halt-on-error",
            tex_path.name,
        ]

    def run_once(command: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            command,
            cwd=workdir,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )

    result = run_once(cmd)
    # Bare pdflatex often needs a second pass; latexmk handles multi-pass itself.
    if not latexmk and result.returncode == 0:
        result = run_once(cmd)

    pdf_path = tex_path.with_suffix(".pdf")
    if result.returncode != 0 or not pdf_path.is_file():
        log = (result.stdout or "") + "\n" + (result.stderr or "")
        raise RuntimeError(f"LaTeX compile failed:\n{log[-4000:]}")

    for ext in (".aux", ".log", ".out", ".fls", ".fdb_latexmk", ".synctex.gz"):
        aux = tex_path.with_suffix(ext)
        if aux.is_file():
            try:
                aux.unlink()
            except OSError:
                pass

    return pdf_path


class Handler(BaseHTTPRequestHandler):
    def _json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def do_GET(self) -> None:  # noqa: N802
        if urlparse(self.path).path == "/health":
            self._json(
                200,
                {
                    "ok": True,
                    "data_dir": str(DATA_DIR),
                    "latexmk": bool(shutil.which("latexmk")),
                    "pdflatex": bool(shutil.which("pdflatex")),
                },
            )
            return
        self._json(404, {"ok": False, "error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if urlparse(self.path).path != "/compile":
            self._json(404, {"ok": False, "error": "not found"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw.decode("utf-8") or "{}")
            rel = data.get("tex") or data.get("path") or ""
            tex_path = _safe_tex_path(rel)
            pdf_path = compile_pdf(tex_path)
            self._json(
                200,
                {
                    "ok": True,
                    "pdf": f"data/output/{pdf_path.name}",
                    "tex": f"data/output/{tex_path.name}",
                },
            )
        except FileNotFoundError as exc:
            self._json(404, {"ok": False, "error": str(exc)})
        except ValueError as exc:
            self._json(400, {"ok": False, "error": str(exc)})
        except Exception as exc:  # noqa: BLE001
            self._json(
                500,
                {
                    "ok": False,
                    "error": str(exc),
                    "trace": traceback.format_exc()[-1500:],
                },
            )


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "output").mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"tex compile server on :{PORT} data_dir={DATA_DIR}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
