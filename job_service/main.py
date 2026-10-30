import os
from uuid import uuid4
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

import httpx
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from llm_adapter import MultiLLMAdapter


app = FastAPI(
    title="Quiz Generator - Job Service",
    description="Tạo và theo dõi trạng thái công việc sinh câu hỏi",
    version="1.0.0",
)

CORE_SERVICE_URL = os.getenv(
    "CORE_SERVICE_URL",
    "http://localhost:8001"
)

jobs: dict[str, dict[str, Any]] = {}


class JobStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class JobCreate(BaseModel):
    document_id: str
    question_count: int = Field(default=5, ge=1, le=50)
    provider: str = "mock"
    model_name: Optional[str] = None


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "job-service"
    }


def update_job(job_id: str, **updates):
    """Cập nhật thông tin và thời điểm thay đổi của job."""
    jobs[job_id].update(updates)
    jobs[job_id]["updated_at"] = datetime.now(timezone.utc).isoformat()


def process_job(job_id: str):
    """Lấy tài liệu, gọi LLM sinh câu hỏi và lưu kết quả."""

    job = jobs[job_id]

    try:
        update_job(job_id, status=JobStatus.processing.value)

        # 1. Lấy nội dung tài liệu từ Core Service
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"{CORE_SERVICE_URL}/api/v1/documents/{job['document_id']}"
            )
            response.raise_for_status()
            document = response.json()

        content = document.get("content", "")

        if not content.strip():
            raise ValueError("Document does not contain any text")

        # 2. Khởi tạo LLM Adapter
        adapter = MultiLLMAdapter(
            provider=job["provider"],
            model_name=job["model_name"]
        )

        # 3. Sinh câu hỏi
        payload, used_model, latency_ms = adapter.generate(
            text=content,
            num_questions=job["question_count"]
        )

        # Chuyển Pydantic model thành dict nếu cần
        quiz_data = (
            payload.model_dump()
            if hasattr(payload, "model_dump")
            else payload
        )

        # 4. Lưu Quiz vào Core Service
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{CORE_SERVICE_URL}/api/v1/quizzes",
                json={
                    "document_id": job["document_id"],
                    "questions": quiz_data["questions"]
                }
            )
            response.raise_for_status()
            saved_quiz = response.json()

        # 5. Đánh dấu job hoàn thành
        update_job(
            job_id,
            status=JobStatus.completed.value,
            result={
                "quiz_id": saved_quiz["quiz_id"],
                "question_count": saved_quiz["question_count"],
                "topic_summary": quiz_data.get("topic_summary", ""),
                "model": used_model,
                "llm_latency_ms": latency_ms
            }
        )

    except Exception as exc:
        update_job(
            job_id,
            status=JobStatus.failed.value,
            error=str(exc)
        )


@app.post("/api/v1/jobs", status_code=202)
def create_job(data: JobCreate, background_tasks: BackgroundTasks):
    job_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()

    job = {
        "job_id": job_id,
        "document_id": data.document_id,
        "question_count": data.question_count,
        "provider": data.provider,
        "model_name": data.model_name,
        "status": JobStatus.queued.value,
        "result": None,
        "error": None,
        "created_at": now,
        "updated_at": now,
    }

    jobs[job_id] = job

    # Đưa công việc vào hàng đợi xử lý nền
    background_tasks.add_task(process_job, job_id)

    return job


@app.get("/api/v1/jobs/{job_id}")
def get_job(job_id: str):
    job = jobs.get(job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )

    return job