import hashlib
from .models import QAMemory
from .database import SessionLocal
from .logger import logger

def get_question_hash(question_text):
    return hashlib.sha256(question_text.lower().strip().encode()).hexdigest()

def get_remembered_answer(question_text):
    q_hash = get_question_hash(question_text)
    db = SessionLocal()
    try:
        record = db.query(QAMemory).filter(QAMemory.question_hash == q_hash).first()
        if record:
            return record.answer_text
        return None
    finally:
        db.close()

def remember_answer(question_text, answer_text):
    q_hash = get_question_hash(question_text)
    db = SessionLocal()
    try:
        record = db.query(QAMemory).filter(QAMemory.question_hash == q_hash).first()
        if record:
            record.answer_text = answer_text
        else:
            record = QAMemory(
                question_hash=q_hash,
                question_text=question_text,
                answer_text=answer_text
            )
            db.add(record)
        db.commit()
    except Exception as e:
        logger.error(f"Error remembering answer: {e}")
        db.rollback()
    finally:
        db.close()
