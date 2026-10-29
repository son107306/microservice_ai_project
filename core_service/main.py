from uuid import uuid4
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(
    title="Quiz Generator - Core Service",
    description="Quản lý tài liệu và kết quả trắc nghiệm",
    version="1.0.0",
)

documents: dict[str, dict[str, Any]] = {}
quizzes: dict[str, dict[str, Any]] = {}


class DocumentCreate(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    page_count: int = Field(ge=1)
    character_count: int = Field(ge=0)



class QuizCreate(BaseModel):
    document_id: str
    questions: list[dict[str, Any]]


@app.get("/health")
def health():
    return {"status": "ok", "service": "core-service"}


@app.post("/api/v1/documents", status_code=201)
def create_document(data : DocumentCreate):
    document_id = str(uuid4())

    document = {
        "document_id": document_id,
        **data.model_dump(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    documents[document_id] = document
    return document



@app.get("/api/v1/documents/{document_id}")
def get_document(document_id: str):
    document = documents.get(document_id)

    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    quiz_id = str(uuid4())

    quiz = {
        "quiz_id": quiz_id,
        "document_id": data.document_id,
        "questions": data.questions,
        "question count": len(data.questions),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    quizzes[quiz_id] = quiz
    return quiz


@app.get("/api/v1/quizzes/{quiz_id}")
def get_quiz(quiz_id: str):
    quiz = quizzes.get(quiz_id)

    if quiz is None:
        raise HTTPException(status_code=404, detail="Quiz not found")

    return quiz