
"""
Project 1 - Tuan 2: Synchronous Baseline
Sinh quiz trac nghiem tu PDF bang FastAPI va Gemini API.
"""

from enum import Enum
import json
import os
import time
from typing import Literal, Optional, List

import pymupdf as fitz
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

app = FastAPI(
    title="PDF Quiz Generator - Baseline",
    description="Sinh cau hoi trac nghiem tu tai lieu PDF",
    version="1.0.0",
)


class LLMProviderType(str, Enum):
    GEMINI = "gemini"
    MOCK = "mock"


class QuizQuestion(BaseModel):
    id: int = Field(..., ge=1)
    question: str
    options: List[str] = Field(..., min_length=4, max_length=4)
    correct_answer: Literal["A", "B", "C", "D"]
    explanation: str = ""


class QuizResponse(BaseModel):
    questions: List[QuizQuestion]


def extract_pdf_text(pdf_bytes: bytes):
    start = time.perf_counter()

    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            page_count = len(doc)
            text = "\n".join(page.get_text() for page in doc)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Khong doc duoc file PDF: {exc}",
        )

    elapsed_ms = (time.perf_counter() - start) * 1000

    if not text.strip():
        raise HTTPException(
            status_code=422,
            detail="PDF khong co lop van ban. Hay thu PDF co the boi den va sao chep chu.",
        )

    return text, page_count, elapsed_ms


def generate_mock_quiz(num_questions: int, delay: float):
    time.sleep(delay)

    questions = []

    for i in range(1, num_questions + 1):
        questions.append(
            QuizQuestion(
                id=i,
                question=f"Cau hoi kiem thu Mock so {i}: "
                         "Day la cau hoi mau cua he thong?",
                options=[
                    "Phuong an A",
                    "Phuong an B",
                    "Phuong an C",
                    "Phuong an D",
                ],
                correct_answer="A",
                explanation="Du lieu mau dung de kiem thu luong xu ly.",
            )
        )

    return questions


def generate_gemini_quiz(
    text: str,
    num_questions: int,
    model_name: str,
    api_key: str,
):
    client = genai.Client(api_key=api_key)

    prompt = f"""
Ban la tro ly tao cau hoi trac nghiem tu tai lieu hoc tap.

Hay tao dung {num_questions} cau hoi dua tren noi dung tai lieu duoi day.
Moi cau co dung 4 phuong an A, B, C, D.
Chi co mot dap an dung cho moi cau.
Khong dua ra thong tin khong co co so trong tai lieu.

Tra ve JSON theo cau truc:
{{
  "questions": [
    {{
      "id": 1,
      "question": "Noi dung cau hoi",
      "options": [
        "A. Phuong an A",
        "B. Phuong an B",
        "C. Phuong an C",
        "D. Phuong an D"
      ],
      "correct_answer": "A",
      "explanation": "Giai thich ngan gon"
    }}
  ]
}}

Tai lieu:
{text[:80000]}
"""

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )

        if not response.text:
            raise ValueError("Gemini khong tra ve noi dung.")

        data = json.loads(response.text)
        result = QuizResponse.model_validate(data)

        if len(result.questions) != num_questions:
            raise ValueError(
                f"Yeu cau {num_questions} cau, "
                f"nhung model tra ve {len(result.questions)} cau."
            )

        for i, question in enumerate(result.questions, start=1):
            question.id = i

        return result.questions

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Loi khi goi Gemini hoac kiem tra JSON: {exc}",
        )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/v1/baseline/generate-quiz")
async def generate_quiz(
    file: UploadFile = File(...),
    provider: LLMProviderType = Form(LLMProviderType.MOCK),
    model_name: str = Form(GEMINI_MODEL),
    num_questions: int = Form(5, ge=1, le=20),
    mock_delay_sec: float = Form(3.0, ge=0, le=30),
    gemini_api_key: Optional[str] = Form(None),
):
    total_start = time.perf_counter()

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Vui long tai len file co duoi .pdf",
        )

    pdf_bytes = await file.read()

    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="File PDF rong.")

    text, page_count, extraction_ms = extract_pdf_text(pdf_bytes)

    llm_start = time.perf_counter()

    if provider == LLMProviderType.MOCK:
        questions = generate_mock_quiz(
            num_questions=num_questions,
            delay=mock_delay_sec,
        )
    else:
        api_key = gemini_api_key or GEMINI_API_KEY

        if not api_key:
            raise HTTPException(
                status_code=400,
                detail="Chua cung cap GEMINI_API_KEY.",
            )

        questions = generate_gemini_quiz(
            text=text,
            num_questions=num_questions,
            model_name=model_name,
            api_key=api_key,
        )

    llm_latency_ms = (time.perf_counter() - llm_start) * 1000
    total_ms = (time.perf_counter() - total_start) * 1000

    return {
        "document_info": {
            "filename": file.filename,
            "page_count": page_count,
            "character_count": len(text),
            "estimated_tokens": (len(text) + 3) // 4,
        },
        "provider": provider.value,
        "model": (
            "mock"
            if provider == LLMProviderType.MOCK
            else model_name
        ),
        "questions": [
            question.model_dump()
            for question in questions
        ],
        "metrics": {
            "extraction_time_ms": round(extraction_ms, 2),
            "llm_latency_ms": round(llm_latency_ms, 2),
            "total_time_ms": round(total_ms, 2),
        },
    }
