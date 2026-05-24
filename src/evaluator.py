import os
import json
import google.generativeai as genai
from dotenv import load_dotenv
from .logger import logger

load_dotenv()

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
    # Using gemini-1.5-flash as the budget-friendly model
    model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-1.5-flash"))
else:
    logger.error("GEMINI_API_KEY not set")
    model = None

def evaluate_match(job_title, job_description, base_resume_content):
    if not model:
        return 0.0, "Gemini API key not configured"
        
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
    Output ONLY the JSON.
    """
    
    try:
        response = model.generate_content(prompt)
        content = response.text.replace("```json", "").replace("```", "").strip()
        result = json.loads(content)
        return result.get("score", 0.0), result.get("reason", "")
    except Exception as e:
        logger.error(f"Error evaluating match with Gemini: {e}")
        return 0.0, f"Evaluation error: {e}"

def tailor_resume(job_description, base_resume_content):
    if not model:
        return base_resume_content
        
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
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logger.error(f"Error tailoring resume with Gemini: {e}")
        return base_resume_content

def answer_application_question(question, job_description, base_resume_content, memory_context=""):
    if not model:
        return "N/A"
        
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
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logger.error(f"Error answering question with Gemini: {e}")
        return "N/A"
