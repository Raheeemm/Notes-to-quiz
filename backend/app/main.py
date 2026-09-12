import io
import json
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from pypdf import PdfReader

from .auth import get_current_user
from .db import NoteSet, get_db, init_db
from .llm import generate_study_set

load_dotenv()


MAX_PDF_SIZE = 10 * 1024 * 1024  # 10 MB


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Notes to Quiz API", lifespan=lifespan)


origins = [
    o.strip()
    for o in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5173"
    ).split(",")
    if o.strip()
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GenerateRequest(BaseModel):
    text: str = Field(min_length=100, max_length=8000)


def extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract selectable text from a PDF."""

    if len(pdf_bytes) > MAX_PDF_SIZE:
        raise HTTPException(
            status_code=413,
            detail="PDF is too large. Maximum size is 10 MB.",
        )

    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Could not read this PDF.",
        )

    pages = []

    for page in reader.pages:
        text = page.extract_text() or ""

        if text.strip():
            pages.append(text.strip())

    extracted = "\n\n".join(pages).strip()

    if len(extracted) < 100:
        raise HTTPException(
            status_code=400,
            detail=(
                "This PDF does not contain enough selectable text. "
                "Scanned or image-only PDFs are not supported yet."
            ),
        )

    # Keep it within the same limit as pasted notes.
    if len(extracted) > 8000:
        extracted = extracted[:8000]

    return extracted


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/generate")
def generate(
    payload: GenerateRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    try:
        study_set = generate_study_set(payload.text)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"The model could not produce a usable quiz. {exc}",
        )

    questions = [q.model_dump() for q in study_set.questions]

    row = NoteSet(
        user_id=user_id,
        source_text=payload.text,
        summary=study_set.summary,
        questions_json=json.dumps(questions),
    )

    db.add(row)
    db.commit()
    db.refresh(row)

    return {
        "id": row.id,
        "summary": row.summary,
        "questions": questions,
        "created_at": row.created_at,
    }


@app.post("/api/generate-pdf")
async def generate_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Please upload a PDF file.",
        )

    pdf_bytes = await file.read()

    text = extract_pdf_text(pdf_bytes)

    try:
        study_set = generate_study_set(text)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"The model could not produce a usable quiz. {exc}",
        )

    questions = [q.model_dump() for q in study_set.questions]

    row = NoteSet(
        user_id=user_id,
        source_text=text,
        summary=study_set.summary,
        questions_json=json.dumps(questions),
    )

    db.add(row)
    db.commit()
    db.refresh(row)

    return {
        "id": row.id,
        "summary": row.summary,
        "questions": questions,
        "created_at": row.created_at,
        "source_name": file.filename,
    }


@app.get("/api/history")
def history(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    rows = (
        db.query(NoteSet)
        .filter(NoteSet.user_id == user_id)
        .order_by(NoteSet.created_at.desc())
        .limit(20)
        .all()
    )

    return {
        "items": [
            {
                "id": r.id,
                "summary": r.summary,
                "questions": json.loads(r.questions_json),
                "created_at": r.created_at,
            }
            for r in rows
        ]
    }