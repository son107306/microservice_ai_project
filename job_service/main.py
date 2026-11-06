import os
import uuid
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from celery import Celery
from shared.database import get_db
from shared.models import Job, Document, Quiz

app = FastAPI(title="Quiz Job Service")

celery_app = Celery(
    "quiz_tasks",
    broker=os.getenv("CELERY_BROKER_URL")
)

@app.post("/api/v1/jobs", status_code=202)
def create_job(
    document_id: str, 
    provider: str = "mock", 
    model_name: str = "mock-llm", 
    question_count: int = 5,
    db: Session = Depends(get_db)
):
    if not 1 <= question_count <= 50:
        raise HTTPException(status_code=400, detail="Số lượng câu hỏi phải từ 1 đến 50")

    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="UUID không hợp lệ")

    doc = db.query(Document).filter(Document.id == doc_uuid).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu")

    new_job = Job(
        document_id=doc_uuid,
        status='queued',
        provider=provider,
        model_name=model_name,
        question_count=question_count
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    
    try:
        celery_app.send_task("worker.tasks.process_quiz_generation", args=[str(new_job.id)])
    except Exception as e:
        new_job.status = 'failed'
        new_job.error_message = f"RabbitMQ Connection Error: {str(e)}"
        db.commit()
        raise HTTPException(status_code=503, detail="Hệ thống hàng đợi đang bận, vui lòng thử lại sau.")
    
    return {
        "message": "Job đã được đưa vào hàng đợi xử lý",
        "job_id": str(new_job.id),
        "status": new_job.status
    }

@app.get("/api/v1/jobs/{job_id}")
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="UUID không hợp lệ")
        
    job = db.query(Job).filter(Job.id == job_uuid).first()
    if not job:
        raise HTTPException(status_code=404, detail="Không tìm thấy Job")
        
    response = {
        "job_id": str(job.id),
        "document_id": str(job.document_id),
        "status": job.status,
        "provider": job.provider,
        "total_time_ms": getattr(job, 'total_time_ms', 0.0),
        "error_message": getattr(job, 'error_message', "")
    }
    
    if job.status == 'completed':
        quiz = db.query(Quiz).filter(Quiz.job_id == job.id).first()
        if quiz:
            response["quiz_id"] = str(quiz.id)
            
    return response