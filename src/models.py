from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import relationship
import enum

class Base(DeclarativeBase):
    pass

class JobStatus(enum.Enum):
    NEW = "new"
    REVIEW = "review"
    APPLIED = "applied"
    REJECTED = "rejected"
    HELP = "help"

class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True)
    job_id_external = Column(String(255), unique=True)
    title = Column(String(255))
    company = Column(String(255))
    location = Column(String(255))
    description = Column(Text)
    url = Column(String(1024))
    source = Column(String(50))
    salary = Column(String(255))
    posted_date = Column(DateTime)
    
    match_score = Column(Float)
    match_reason = Column(Text)
    status = Column(Enum(JobStatus), default=JobStatus.NEW)
    
    tailored_resume_path = Column(String(1024))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    questions = relationship("ApplicationQuestion", back_populates="job")

class ApplicationQuestion(Base):
    __tablename__ = "application_questions"
    
    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey("jobs.id"))
    question_text = Column(Text)
    answer_text = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    job = relationship("Job", back_populates="questions")

class QAMemory(Base):
    __tablename__ = "qa_memory"
    
    id = Column(Integer, primary_key=True)
    question_hash = Column(String(64), unique=True)
    question_text = Column(Text)
    answer_text = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class RunLog(Base):
    __tablename__ = "run_logs"
    
    id = Column(Integer, primary_key=True)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)
    status = Column(String(50))
    jobs_found = Column(Integer, default=0)
    jobs_applied = Column(Integer, default=0)
    error_message = Column(Text)
