import os
import time
import uuid
from celery import Celery
from shared.database import SessionLocal
from shared.models import Job, Quiz, Question, Document
from preprocessor import extract_document
from llm_adapter import MultiLLMAdapter
from sqlalchemy.exc import IntegrityError

celery_app = Celery(
    "quiz_tasks",
    broker=os.getenv("CELERY_BROKER_URL")
)

celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True
)

@celery_app.task(bind=True, max_retries=3, name="worker.tasks.process_quiz_generation")
def process_quiz_generation(self, job_id_str: str):
    try:
        job_uuid = uuid.UUID(str(job_id_str))
    except (ValueError, TypeError, AttributeError):
        return {
            "status": "invalid_job_id",
            "job_id": str(job_id_str)
        }

    db = SessionLocal()
    start_time = time.perf_counter()

    try:
        job = db.query(Job).filter(Job.id == job_uuid).first()
        if not job:
            return

        existing_quiz = db.query(Quiz).filter(Quiz.job_id == job_uuid).first()
        if existing_quiz:
            job.status = "completed"
            job.error_message = None
            db.commit()
            return {
                "status": "completed",
                "job_id": str(job.id),
                "quiz_id": str(existing_quiz.id)
            }

        job.status = 'processing'
        db.commit()

        doc = db.query(Document).filter(Document.id == job.document_id).first()
        if not doc or not os.path.exists(doc.file_path):
            raise FileNotFoundError("Tài liệu không tồn tại trên ổ đĩa chung")

        with open(doc.file_path, "rb") as f:
            file_bytes = f.read()

        extracted_text = extract_document(file_bytes, doc.filename)
        doc.character_count = len(extracted_text)

        provider = getattr(job, 'provider', 'mock')
        adapter = MultiLLMAdapter(provider=provider, model_name=job.model_name)
        num_questions = getattr(job, 'question_count', 5)
        
        payload, used_model, llm_latency = adapter.generate(extracted_text, num_questions=num_questions)

        if not payload.questions:
            raise ValueError("LLM không tạo được câu hỏi")
        for q in payload.questions:
            if len(q.options) != 4:
                raise ValueError(f"Câu hỏi '{q.question}' không có đủ 4 lựa chọn")
            if q.correct_answer not in ["A", "B", "C", "D"]:
                raise ValueError(f"Đáp án '{q.correct_answer}' không hợp lệ")

        new_quiz = Quiz(
            job_id=job.id,
            document_id=job.document_id,
            topic_summary=payload.topic_summary,
            question_count=len(payload.questions)
        )
        db.add(new_quiz)
        db.flush()

        # Dùng enumerate để tạo question_order an toàn
        for index, q in enumerate(payload.questions, start=1):
            new_question = Question(
                quiz_id=new_quiz.id,
                question_order=index,
                question_text=q.question,
                option_a=q.options[0],
                option_b=q.options[1],
                option_c=q.options[2],
                option_d=q.options[3],
                correct_answer=q.correct_answer,
                explanation=q.explanation
            )
            db.add(new_question)

        job.status = 'completed'
        job.llm_latency_ms = llm_latency
        job.total_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
        job.error_message = None
        db.commit()

    except Exception as e:
        db.rollback()
        
        try:
            job_update = db.query(Job).filter(Job.id == job_uuid).first()
            if job_update:
                if self.request.retries < self.max_retries:
                    job_update.status = "queued"
                    job_update.retry_count = self.request.retries + 1
                    job_update.error_message = str(e)
                else:
                    job_update.status = "failed"
                    job_update.error_message = str(e)
                db.commit()
        except Exception:
            db.rollback()

        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=5 * (2 ** self.request.retries))
        else:
            raise e
            
    finally:
        db.close()