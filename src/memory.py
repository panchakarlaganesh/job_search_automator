from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from src.database import Base, SessionLocal

class QuestionAnswer(Base):
    __tablename__ = "question_memory"
    
    id = Column(Integer, primary_key=True)
    question = Column(Text, unique=True, nullable=False)
    answer = Column(Text, nullable=False)
    category = Column(String(50), default="general")
    created_at = Column(DateTime, default=datetime.utcnow)

def save_qa(question, answer, category="general"):
    db = SessionLocal()
    try:
        # Check if question exists
        existing = db.query(QuestionAnswer).filter(QuestionAnswer.question == question).first()
        if existing:
            existing.answer = answer
            existing.category = category
        else:
            new_qa = QuestionAnswer(question=question, answer=answer, category=category)
            db.add(new_qa)
        db.commit()
    finally:
        db.close()

def get_answer(question):
    db = SessionLocal()
    try:
        qa = db.query(QuestionAnswer).filter(QuestionAnswer.question == question).first()
        return qa.answer if qa else None
    finally:
        db.close()

def get_all_qa():
    db = SessionLocal()
    try:
        return db.query(QuestionAnswer).all()
    finally:
        db.close()
