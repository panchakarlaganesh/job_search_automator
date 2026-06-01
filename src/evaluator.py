import os
import json
import requests
import re
import warnings
from dotenv import load_dotenv
from src.logger import logger

# Suppress deprecation warnings from older SDKs if still present in dependencies
warnings.filterwarnings("ignore", category=FutureWarning, module="google.generativeai")

load_dotenv()

USE_LOCAL_LLM = os.getenv("USE_LOCAL_LLM", "true").lower() == "true"
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")

# Try to use the new google-genai SDK if available, fallback to google-generativeai
try:
    from google import genai
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY")) if os.getenv("GEMINI_API_KEY") else None
    GEMINI_MODEL_ID = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    HAS_NEW_SDK = True
except ImportError:
    import google.generativeai as old_genai
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        old_genai.configure(api_key=api_key)
        gemini_model = old_genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-1.5-flash"))
    else:
        gemini_model = None
    HAS_NEW_SDK = False

def clean_json_response(text):
    if not text: return ""
    # Remove markdown code blocks if present
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'\s*```', '', text)
    match = re.search(r'(\[.*\]|\{.*\})', text, re.DOTALL)
    if match: return match.group(1)
    return text

def call_llm(prompt, json_mode=False):
    if USE_LOCAL_LLM:
        payload = {"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}
        if json_mode: payload["format"] = "json"
        try:
            response = requests.post(OLLAMA_URL, json=payload, timeout=120)
            response.raise_for_status()
            return response.json().get("response", "")
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            return None
    else:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.error("GEMINI_API_KEY not found. Please set it in your environment or GitHub Secrets.")
            return None

        try:
            if HAS_NEW_SDK:
                response = client.models.generate_content(
                    model=GEMINI_MODEL_ID,
                    contents=prompt
                )
                return response.text
            else:
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
    Return a JSON list of objects, each containing:
    - 'id': The JOB ID provided (as a number).
    - 'score': A float between 0 and 1.
    - 'reason': A brief explanation.
    - 'seniority': One of [Entry, Junior, Mid, Senior, Lead, Staff, Principal, Manager].
    - 'tech_stack': A list of top 5 technologies mentioned.
    - 'salary_estimate': Any salary info mentioned (or "Not specified").

    Example format:
    [
      {{
        "id": 1, 
        "score": 0.8, 
        "reason": "Matches core skills.", 
        "seniority": "Senior", 
        "tech_stack": ["AWS", "Kubernetes", "Python"], 
        "salary_estimate": "$150k - $200k"
      }}
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
