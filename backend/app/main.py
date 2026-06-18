"""Gradaroo resume converter API.
POST /convert  (multipart: file=<pdf>)  ->  .docx download
Free tier: one conversion, no auth, nothing stored."""

import os
import logging
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware

from app.parser import parse_resume
from app.renderer import build_docx

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("converter")

MAX_BYTES = 5 * 1024 * 1024  # 5 MB
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")

app = FastAPI(title="Gradaroo Resume Converter")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000").split(",") if o],
    allow_methods=["POST"],
    allow_headers=["*"],
)


def _extract_pdf_text(raw: bytes) -> str:
    from pypdf import PdfReader
    import io
    reader = PdfReader(io.BytesIO(raw))
    return "\n".join((pg.extract_text() or "") for pg in reader.pages)


@app.get("/health")
def health():
    return {"ok": True, "key_configured": bool(GEMINI_KEY)}


@app.post("/convert")
async def convert(file: UploadFile = File(...)):
    if not GEMINI_KEY:
        raise HTTPException(500, "Server not configured: missing GEMINI_API_KEY.")
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(400, "Please upload a PDF.")

    raw = await file.read()
    if len(raw) > MAX_BYTES:
        raise HTTPException(413, "That PDF is too large (max 5 MB).")

    try:
        text = _extract_pdf_text(raw)
    except Exception:
        raise HTTPException(400, "Couldn't read that PDF.")
    if len(text.strip()) < 40:
        raise HTTPException(422, "No readable text found (is it a scanned image?).")

    try:
        data = parse_resume(text, GEMINI_KEY)
    except RuntimeError as e:
        log.warning("parse failed: %s", e)
        raise HTTPException(503, "AI is busy right now. Please try again in a moment.")

    if not data.get("name") and not data.get("experience"):
        raise HTTPException(422, "Couldn't confidently read that resume. Try a clearer PDF.")

    docx_bytes = build_docx(data)
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": 'attachment; filename="resume-australian-format.docx"'},
    )
