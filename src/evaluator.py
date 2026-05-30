import os
import json
import requests
import re
import google.generativeai as genai
from dotenv import load_dotenv
from src.logger import logger

load_dotenv()

USE_LOCAL_LLM = os.getenv("USE_LOCAL_LLM", "true").lower() == "true"
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")

api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
    gemini_model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-1.5-flash"))
else:
    gemini_model = None

def clean_json_response(text):
    if not text: return ""
    match = re.search(r'(\[.*\]|\{.*\})', text, re.DOTALL)
    if match: return match.group(1)
    return text

def call_llm(prompt, json_mode=False):
    if USE_LOCAL_LLM:
        payload = {"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}
        if json_mode: payload["format"] = "json"
        try:
            response = requests.post(OLLAMA_URL, json=payload, timeout=90)
            response.raise_for_status()
            return response.json().get("response", "")
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            return None
    else:
        if not gemini_model: 
            logger.error("Gemini model not configured but USE_LOCAL_LLM is false.")
            return None
        try:
            response = gemini_model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Gemini error: {e}")
            return None

def evaluate_match(job_description, base_resume_content):
    prompt = f"""
    Evaluate the match between the following job description and the candidate's resume.
    
    Job Description:
    {job_description[:2000]}
    
    Resume:
    {base_resume_content[:2000]}
    
    Return a JSON object with:
    - 'score': A float between 0 and 1 representing the match quality.
    - 'reason': A brief explanation for the score.
    """
    response_text = call_llm(prompt, json_mode=True)
    try:
        cleaned = clean_json_response(response_text)
        return json.loads(cleaned)
    except Exception as e:
        logger.error(f"Failed to parse evaluation response: {e}")
        return {"score": 0.0, "reason": "Error parsing LLM response"}

def batch_evaluate_matches(jobs_data, base_resume_content):
    if not jobs_data: return []
    
    # If there are many jobs, we might still want to do individual or smaller batches
    # For now, let's implement a simple batch prompt
    jobs_str = ""
    for job in jobs_data:
        jobs_str += f"--- JOB (ID: {job['id']}) ---\nTitle: {job['title']}\nDescription: {job['description'][:1000]}\n\n"

    prompt = f"""
    Evaluate the match between the candidate resume and these jobs.
    
    Resume:
    {base_resume_content[:2000]}
    
    Jobs:
    {jobs_str}
    
    CRITICAL: Return ONLY a valid JSON list of objects. Do not include any other text, markdown blocks, or explanations.
    Each object must have:
    - 'id': The JOB ID provided (as a number).
    - 'score': A float between 0 and 1.
    - 'reason': A brief explanation.
    
    Example format:
    [
      {{"id": 1, "score": 0.8, "reason": "Matches core skills."}},
      {{"id": 2, "score": 0.2, "reason": "Lack of required experience."}}
    ]
    """
    
    response_text = call_llm(prompt, json_mode=True)

    try:
        cleaned = clean_json_response(response_text)
        data = json.loads(cleaned)
        return data if isinstance(data, list) else [data]
    except Exception as e:
        logger.error(f"Failed to parse batch evaluation response: {e}")
        logger.debug(f"Raw response: {response_text}")
        return []

def tailor_resume(job_description, base_resume_content):
    prompt = f"""
    You are an expert resume writer. Tailor the following resume to match the job description provided.
    
    GUIDELINES:
    1. Maintain 100% truthfulness. Do not invent experience.
    2. Adjust the 'Summary' to highlight keywords from the job description.
    3. Reorder or emphasize skills that are mentioned as 'Required' or 'Preferred'.
    4. For 'Experience' bullet points, rephrase them to use impactful action verbs and quantify results if possible, focusing on aspects relevant to the job.
    5. Maintain a professional, clean SINGLE-COLUMN Markdown format.
    6. DO NOT use tables, columns, or side-by-side text.
    7. Ensure the tailoring is significant (around 30% change in phrasing/emphasis).

    Job Description:
    {job_description[:3000]}
    
    Base Resume:
    {base_resume_content[:4000]}
    
    Output ONLY the tailored resume in Markdown. Do not include any intro/outro text.
    """
    return call_llm(prompt) or base_resume_content
