import os
import json
import requests
import google.generativeai as genai
from dotenv import load_dotenv
from .logger import logger

load_dotenv()

# Settings
USE_LOCAL_LLM = os.getenv("USE_LOCAL_LLM", "true").lower() == "true"
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")

# Gemini Config
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
    gemini_model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-1.5-flash"))
else:
    gemini_model = None

def call_local_llm(prompt, json_mode=False):
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }
    if json_mode:
        payload["format"] = "json"
        
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=90) # Increased timeout for 7b model
        response.raise_for_status()
        return response.json().get("response", "")
    except Exception as e:
        logger.error(f"Ollama error: {e}")
        return None

def batch_evaluate_matches(jobs_data, base_resume_content):
    if not jobs_data:
        return []
        
    jobs_str = ""
    for i, job in enumerate(jobs_data):
        jobs_str += f"--- JOB {i} (ID: {job['id']}) ---\nTitle: {job['title']}\nDescription: {job['description'][:1000]}\n\n"

    prompt = f"""
    Evaluate the match between the following jobs and the candidate's resume.
    
    Candidate Resume:
    {base_resume_content}
    
    Jobs to Evaluate:
    {jobs_str}
    
    Return a JSON list of objects. Each object MUST have:
    "id" (int), "score" (float 0-1), and "reason" (string).
    Output ONLY the JSON list.
    """
    
    response_text = ""
    if USE_LOCAL_LLM:
        logger.info(f"Using local LLM ({OLLAMA_MODEL}) for batch evaluation...")
        response_text = call_local_llm(prompt, json_mode=True)
    else:
        logger.warning("!!! Hitting Gemini API (Paid) for batch evaluation !!!")
        if not gemini_model: return []
        response = gemini_model.generate_content(prompt)
        response_text = response.text.replace("```json", "").replace("```", "").strip()

    if not response_text:
        return []

    try:
        return json.loads(response_text)
    except Exception as e:
        logger.error(f"JSON Parse error: {e}. Raw response: {response_text[:200]}")
        return []

def evaluate_match(job_title, job_description, base_resume_content):
    """Fallback for single job evaluation"""
    results = batch_evaluate_matches([{'id': 0, 'title': job_title, 'description': job_description}], base_resume_content)
    if results:
        return results[0].get("score", 0.0), results[0].get("reason", "")
    return 0.0, "Evaluation failed"

def tailor_resume(job_description, base_resume_content):
    prompt = f"""
    Modify this resume to match the job description. 
    Adjust about 30% of content. Keep Markdown format.
    
    Job: {job_description[:1000]}
    Resume: {base_resume_content}
    
    Return ONLY the modified Markdown.
    """
    
    if USE_LOCAL_LLM:
        logger.info(f"Using local LLM ({OLLAMA_MODEL}) for tailoring...")
        return call_local_llm(prompt) or base_resume_content
    else:
        logger.warning("!!! Hitting Gemini API (Paid) for tailoring !!!")
        if not gemini_model: return base_resume_content
        response = gemini_model.generate_content(prompt)
        return response.text

def answer_application_question(question, job_description, base_resume_content):
    prompt = f"""
    Answer this job application question based on the resume.
    Question: {question}
    Resume: {base_resume_content}
    Return ONLY the answer text.
    """
    if USE_LOCAL_LLM:
        return call_local_llm(prompt) or "N/A"
    else:
        if not gemini_model: return "N/A"
        return gemini_model.generate_content(prompt).text.strip()
