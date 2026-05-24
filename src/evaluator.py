import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from .logger import logger

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = os.getenv("LLM_MODEL", "gpt-4o")

def evaluate_match(job_title, job_description, base_resume_content):
    prompt = f"""
    You are an expert technical recruiter. Evaluate the match between the following job description and the candidate's resume.
    
    Job Title: {job_title}
    Job Description:
    {job_description}
    
    Candidate Resume:
    {base_resume_content}
    
    Return a JSON object with:
    1. "score": A float between 0 and 1 representing the match percentage (0.6 means 60% match).
    2. "reason": A brief explanation of the score, highlighting missing or matching key skills.
    
    Match based on technical skills, experience level, and core responsibilities.
    """
    
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        result = json.loads(response.choices[0].message.content)
        return result.get("score", 0.0), result.get("reason", "")
    except Exception as e:
        logger.error(f"Error evaluating match: {e}")
        return 0.0, f"Evaluation error: {e}"

def tailor_resume(job_description, base_resume_content):
    prompt = f"""
    You are an expert resume writer. Modify the following resume to better align with the job description.
    Ensure that about 30% of the content is adjusted to highlight relevant keywords and experiences without lying.
    Maintain the overall structure and format (Markdown).
    
    Job Description:
    {job_description}
    
    Base Resume (Markdown):
    {base_resume_content}
    
    Return ONLY the modified Markdown content.
    """
    
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error tailoring resume: {e}")
        return base_resume_content

def answer_application_question(question, job_description, base_resume_content, memory_context=""):
    prompt = f"""
    You are applying for a job. Based on the job description and your resume, answer the following application question professionally.
    
    Question: {question}
    
    Job Description:
    {job_description}
    
    Your Resume:
    {base_resume_content}
    
    {f"Previous context/memory: {memory_context}" if memory_context else ""}
    
    Return ONLY the answer text. Be concise but thorough.
    """
    
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Error answering question: {e}")
        return "N/A"
