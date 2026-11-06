import os
import uuid
import shutil
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from shared.database import get_db
from shared.models import Document, Quiz, Question

app = FastAPI(title="Quiz Core Service")
UPLOAD_DIR = "/app/storage/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Giới hạn dung lượng file: 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024 

@app.post("/api/v1/documents/upload")
def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    file_path = None
    try:
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in [".pdf", ".docx", ".pptx"]:
            raise HTTPException(status_code=400, detail="Chỉ hỗ trợ .pdf, .docx, .pptx")
            
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)
        
        # Kiểm tra dung lượng
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="Dung lượng file vượt quá giới hạn 10MB")

        file_id = uuid.uuid4()
        saved_filename = f"{file_id}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, saved_filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        new_doc = Document(
            id=file_id,
            filename=file.filename,
            file_type=file_ext,
            file_path=file_path,
            file_size=file_size,
            character_count=0 
        )
        db.add(new_doc)
        db.commit()
        db.refresh(new_doc)
        
        return {"message": "Upload thành công", "document_id": str(new_doc.id)}
        
    except HTTPException:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        raise
    except Exception as e:
        db.rollback()
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Lỗi hệ thống khi upload: {str(e)}")

@app.get("/api/v1/documents/{document_id}")
def get_document(document_id: str, db: Session = Depends(get_db)):
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="UUID không hợp lệ")
        
    doc = db.query(Document).filter(Document.id == doc_uuid).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu")
        
    return {
        "document_id": str(doc.id),
        "filename": doc.filename,
        "file_type": doc.file_type,
        "file_size_bytes": doc.file_size
    }

@app.get("/api/v1/quizzes/{quiz_id}")
def get_quiz_result(quiz_id: str, db: Session = Depends(get_db)):
    try:
        quiz_uuid = uuid.UUID(quiz_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="UUID không hợp lệ")

    quiz = db.query(Quiz).filter(Quiz.id == quiz_uuid).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Không tìm thấy Quiz")

    questions = db.query(Question).filter(Question.quiz_id == quiz.id).order_by(Question.question_order).all()

    questions_list = []
    for q in questions:
        questions_list.append({
            "id": q.question_order,
            "question": q.question_text,
            "options": [q.option_a, q.option_b, q.option_c, q.option_d],
            "correct_answer": q.correct_answer,
            "explanation": q.explanation
        })

    return {
        "quiz_id": str(quiz.id),
        "job_id": str(quiz.job_id),
        "document_id": str(quiz.document_id),
        "topic_summary": quiz.topic_summary,
        "question_count": quiz.question_count,
        "questions": questions_list
    }