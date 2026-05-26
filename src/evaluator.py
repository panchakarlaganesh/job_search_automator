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
    
    Return a JSON list of objects, each containing:
    - 'id': The JOB ID provided.
    - 'score': A float between 0 and 1.
    - 'reason': A brief explanation.
    """
    
    response_text = call_llm(prompt, json_mode=True)

    try:
        cleaned = clean_json_response(response_text)
        data = json.loads(cleaned)
        return data if isinstance(data, list) else [data]
    except Exception as e:
        logger.error(f"Failed to parse batch evaluation response: {e}")
        return []

def tailor_resume(job_description, base_resume_content):
    prompt = f"""
    Tailor the following resume to better match the job description. 
    Maintain truthfulness but highlight relevant experience.
    Return the tailored resume in Markdown format.
    
    Job Description:
    {job_description[:2000]}
    
    Resume:
    {base_resume_content[:3000]}
    """
    return call_llm(prompt) or base_resume_content
