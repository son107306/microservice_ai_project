
import os
import time
import uuid

from celery import Celery

from shared.database import SessionLocal
from shared.models import Job, Quiz, Question, Document

from preprocessor import extract_document
from chunking import chunk_text
from llm_adapter import MultiLLMAdapter, QuizPayload, QuizQuestion


# ============================================================
# 1. CELERY CONFIGURATION
# ============================================================

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


# ============================================================
# 2. CHUNK ALLOCATION
# ============================================================

def allocate_chunks(chunks, num_questions):
    """
    Phân bổ số câu hỏi cần sinh cho từng chunk.
    """

    if not chunks or num_questions <= 0:
        return []

    total_chunks = len(chunks)

    if total_chunks <= num_questions:
        base = num_questions // total_chunks
        remainder = num_questions % total_chunks

        return [
            (
                chunk,
                base + (1 if i < remainder else 0)
            )
            for i, chunk in enumerate(chunks)
        ]

    if num_questions == 1:
        indexes = [total_chunks // 2]

    else:
        indexes = [
            round(
                i * (total_chunks - 1) / (num_questions - 1)
            )
            for i in range(num_questions)
        ]

    return [
        (chunks[i], 1)
        for i in indexes
    ]


# ============================================================
# 3. REMOVE DUPLICATE QUESTIONS
# ============================================================

def remove_duplicate_questions(questions):
    """
    Loại bỏ câu hỏi trùng lặp dựa trên nội dung.
    """

    unique_questions = []
    seen = set()

    for question in questions:
        normalized = " ".join(
            question.question.casefold().split()
        )

        if not normalized:
            continue

        if normalized in seen:
            continue

        seen.add(normalized)
        unique_questions.append(question)

    return unique_questions


# ============================================================
# 4. MAIN QUIZ GENERATION TASK
# ============================================================

@celery_app.task(
    bind=True,
    max_retries=0,
    name="worker.tasks.process_quiz_generation"
)
def process_quiz_generation(self, job_id_str: str):

    # --------------------------------------------------------
    # VALIDATE JOB ID
    # --------------------------------------------------------

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

        # ----------------------------------------------------
        # 1. FIND JOB
        # ----------------------------------------------------

        job = (
            db.query(Job)
            .filter(Job.id == job_uuid)
            .first()
        )

        if not job:
            return {
                "status": "job_not_found",
                "job_id": str(job_uuid)
            }

        # ----------------------------------------------------
        # 2. IDEMPOTENCY CHECK
        # ----------------------------------------------------

        existing_quiz = (
            db.query(Quiz)
            .filter(Quiz.job_id == job_uuid)
            .first()
        )

        if existing_quiz:
            job.status = "completed"
            job.error_message = None

            db.commit()

            return {
                "status": "completed",
                "job_id": str(job.id),
                "quiz_id": str(existing_quiz.id)
            }

        # ----------------------------------------------------
        # 3. UPDATE JOB STATUS
        # ----------------------------------------------------

        job.status = "processing"
        job.error_message = None

        db.commit()

        # ----------------------------------------------------
        # 4. LOAD DOCUMENT
        # ----------------------------------------------------

        doc = (
            db.query(Document)
            .filter(Document.id == job.document_id)
            .first()
        )

        if not doc or not os.path.exists(doc.file_path):
            raise FileNotFoundError(
                "Tài liệu không tồn tại trên ổ đĩa chung"
            )

        with open(doc.file_path, "rb") as f:
            file_bytes = f.read()

        # ----------------------------------------------------
        # 5. EXTRACT TEXT
        # ----------------------------------------------------

        extracted_text = extract_document(
            file_bytes,
            doc.filename
        )

        if not extracted_text.strip():
            raise ValueError(
                "Không trích xuất được nội dung từ tài liệu"
            )

        doc.character_count = len(extracted_text)

        # ----------------------------------------------------
        # 6. INITIALIZE LLM ADAPTER
        # ----------------------------------------------------

        provider = getattr(job, "provider", None) or "mock"

        adapter = MultiLLMAdapter(
            provider=provider,
            model_name=job.model_name
        )

        num_questions = (
            getattr(job, "question_count", None) or 5
        )

        if not 1 <= num_questions <= 50:
            raise ValueError(
                "question_count phải nằm trong khoảng 1-50"
            )

        # ----------------------------------------------------
        # 7. CHUNK DOCUMENT
        # ----------------------------------------------------

        chunks = chunk_text(
            extracted_text,
            chunk_size=5000,
            overlap=300
        )

        if not chunks:
            raise ValueError(
                "Không có nội dung để tạo câu hỏi"
            )

        chunk_allocations = allocate_chunks(
            chunks,
            num_questions
        )

        all_questions = []
        summaries = []
        total_llm_latency = 0

        # ----------------------------------------------------
        # 8. GENERATE QUESTIONS FROM EACH CHUNK
        # ----------------------------------------------------

        for chunk, question_count in chunk_allocations:

            result = adapter.generate(
                chunk,
                num_questions=question_count
            )

            payload_part = result["payload"]
            total_llm_latency += result["latency_ms"]

            if payload_part.topic_summary:
                summaries.append(
                    payload_part.topic_summary
                )

            all_questions.extend(
                payload_part.questions
            )

        # ----------------------------------------------------
        # 9. REMOVE DUPLICATES
        # ----------------------------------------------------

        all_questions = remove_duplicate_questions(
            all_questions
        )

        missing = num_questions - len(all_questions)

        # ----------------------------------------------------
        # 10. GENERATE EXTRA QUESTIONS IF NECESSARY
        # ----------------------------------------------------

        if missing > 0:

            selected_text = "\n\n".join(
                chunk
                for chunk, _ in chunk_allocations
            )

            extra_result = adapter.generate(
                selected_text,
                num_questions=missing
            )

            extra_payload = extra_result["payload"]

            total_llm_latency += (
                extra_result["latency_ms"]
            )

            all_questions.extend(
                extra_payload.questions
            )

            if extra_payload.topic_summary:
                summaries.append(
                    extra_payload.topic_summary
                )

            all_questions = remove_duplicate_questions(
                all_questions
            )

        # ----------------------------------------------------
        # 11. CHECK QUESTION COUNT
        # ----------------------------------------------------

        if len(all_questions) < num_questions:
            raise ValueError(
                f"Chỉ tạo được {len(all_questions)}/"
                f"{num_questions} câu hỏi khác nhau"
            )

        all_questions = all_questions[:num_questions]

        # ----------------------------------------------------
        # 12. BUILD FINAL PAYLOAD
        # ----------------------------------------------------

        final_questions = [
            QuizQuestion(
                id=index,
                question=q.question,
                options=q.options,
                correct_answer=q.correct_answer,
                explanation=q.explanation
            )
            for index, q in enumerate(
                all_questions,
                start=1
            )
        ]

        payload = QuizPayload(
            topic_summary="\n".join(
                dict.fromkeys(summaries)
            ),
            questions=final_questions
        )

        if not payload.questions:
            raise ValueError(
                "LLM không tạo được câu hỏi"
            )

        # ----------------------------------------------------
        # 13. VALIDATE QUESTIONS
        # ----------------------------------------------------

        for q in payload.questions:

            if not q.question.strip():
                raise ValueError(
                    "Nội dung câu hỏi không được để trống"
                )

            if len(q.options) != 4:
                raise ValueError(
                    f"Câu hỏi '{q.question}' "
                    "không có đủ 4 lựa chọn"
                )

            if q.correct_answer not in ["A", "B", "C", "D"]:
                raise ValueError(
                    f"Đáp án '{q.correct_answer}' không hợp lệ"
                )

        # ----------------------------------------------------
        # 14. CREATE QUIZ
        # ----------------------------------------------------

        new_quiz = Quiz(
            job_id=job.id,
            document_id=job.document_id,
            topic_summary=payload.topic_summary,
            question_count=len(payload.questions)
        )

        db.add(new_quiz)
        db.flush()

        # ----------------------------------------------------
        # 15. SAVE QUESTIONS
        # ----------------------------------------------------

        for index, q in enumerate(
            payload.questions,
            start=1
        ):

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

        # ----------------------------------------------------
        # 16. COMPLETE JOB
        # ----------------------------------------------------

        job.status = "completed"

        job.llm_latency_ms = total_llm_latency

        job.total_time_ms = round(
            (time.perf_counter() - start_time) * 1000,
            2
        )

        job.error_message = None

        db.commit()

        return {
            "status": "completed",
            "job_id": str(job.id),
            "quiz_id": str(new_quiz.id),
            "question_count": len(payload.questions),
            "chunk_count": len(chunks),
            "llm_latency_ms": total_llm_latency,
            "total_time_ms": job.total_time_ms
        }

    # --------------------------------------------------------
    # ERROR HANDLING
    # --------------------------------------------------------

    except Exception as e:

        db.rollback()

        try:
            job_update = (
                db.query(Job)
                .filter(Job.id == job_uuid)
                .first()
            )

            if job_update:
                job_update.status = "failed"
                job_update.error_message = str(e)

                db.commit()

        except Exception:
            db.rollback()

        raise

    finally:
        db.close()
