from uuid import uuid4
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(
    title="Quiz Generator - Job Service",
    description="Tạo và theo dõi trạng thái công việc sinh câu hỏi",
    version="1.0.0",
)


class JobStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class JobCreate(BaseModel):
    document_id: str
    question_count: int = Field(default=5, ge=1, le=50)


jobs: dict[str,dict[str, Any]] = {}


@app.get("/health")
def health():
    return {"status": "ok", "service": "job-service"}


@app.post("/api/v1/jobs", status_code=202)
def create_job(data : JobCreate):
    job_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()

    job = {
        "job_id": job_id,
        "document_id": data.document_id,
        "question_count": data.question_count,
        "status": JobStatus.queued.value,
        "result": None,
        "error": None,
        "created_at": now,
        "updated_at": now,
    }

    jobs[job_id] = job

    return job 


@app.get("/api/v1/jobs/{job_id}")
def get_job(job_id: str):
    job = jobs.get(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return job