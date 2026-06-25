import os
import json
import requests
import re
import warnings
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from dotenv import load_dotenv
from src.logger import logger

load_dotenv()

USE_LOCAL_LLM = os.getenv("USE_LOCAL_LLM", "true").lower() == "true"
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma2:2b")

# Try to use the new google-genai SDK if available
try:
    from google import genai
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY")) if os.getenv("GEMINI_API_KEY") else None
    GEMINI_MODEL_ID = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    HAS_NEW_SDK = True
except ImportError:
    import google.generativeai as old_genai
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        old_genai.configure(api_key=api_key)
        gemini_model = old_genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))
    else:
        gemini_model = None
    HAS_NEW_SDK = False

def clean_json_response(text):
    if not text: return ""
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'\s*```', '', text)
    match = re.search(r'(\[.*\]|\{.*\})', text, re.DOTALL)
    if match: return match.group(1)
    return text

def call_llm(prompt, json_mode=False):
    sarvam_key = os.getenv("SARVAM_API_KEY")
    if sarvam_key:
        model = os.getenv("SARVAM_MODEL", "sarvam-105b")
        url = "https://api.sarvam.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {sarvam_key.strip()}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
            
        try:
            logger.info(f"Sarvam AI: Sending request to {model}...")
            response = requests.post(url, json=payload, headers=headers, timeout=120)
            response.raise_for_status()
            res_json = response.json()
            return res_json["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Sarvam AI error: {e}")
            # Fall back to Gemini/Ollama if Sarvam fails

    if USE_LOCAL_LLM:
        payload = {"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}
        if json_mode: payload["format"] = "json"
        try:
            logger.info(f"Ollama: Sending request to {OLLAMA_MODEL}...")
            response = requests.post(OLLAMA_URL, json=payload, timeout=300)
            response.raise_for_status()
            return response.json().get("response", "")
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            return None
    else:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key: return None
        try:
            if HAS_NEW_SDK:
                response = client.models.generate_content(model=GEMINI_MODEL_ID, contents=prompt)
                return response.text
            else:
                response = gemini_model.generate_content(prompt)
                return response.text
        except Exception as e:
            logger.error(f"Gemini error: {e}")
            return None

def calculate_nlp_similarity(text1, text2):
    """Calculates TF-IDF cosine similarity between two texts."""
    try:
        vectorizer = TfidfVectorizer(stop_words='english')
        tfidf = vectorizer.fit_transform([text1, text2])
        return cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]
    except Exception as e:
        logger.warning(f"Similarity calculation failed: {e}")
        return 0.0

def evaluate_match(job_description, base_resume_content):
    # 1. Quick NLP Check
    nlp_score = calculate_nlp_similarity(job_description.lower(), base_resume_content.lower())
    
    # 2. Keyword Boost (Candidate is preparing for/has experience in these)
    prioritized_keywords = ["terraform", "ansible", "aws", "production support", "application support", "github actions"]
    found_priority = [k for k in prioritized_keywords if k in job_description.lower()]
    
    # Boost nlp_score if priority keywords are in JD (0.05 per keyword found)
    nlp_score += (len(found_priority) * 0.05)
    nlp_score = min(nlp_score, 1.0)

    # 3. AI Reasoning Pass (Grounded in NLP score)
    prompt = f"""
    You are an ATS Scoring Algorithm. Evaluate the match between the Job Description and the Resume.
    
    --- CANDIDATE EXPERTISE NOTES ---
    - Candidate is a Lead SRE with 10+ years experience.
    - Candidate has EXTENSIVE experience in Production Support and Application Support.
    - IMPORTANT: Candidate is actively preparing for Terraform, Ansible, AWS, and GitHub Actions. 
    - TREAT 'Terraform', 'Ansible', 'AWS', 'Production Support', 'Application Support', and 'GitHub Actions' as FULL MATCHES if they appear in the JD.
    - Treat 'Terraform', 'Ansible' as 'IaC'.
    - Treat 'Splunk', 'Grafana', 'Prometheus' as 'Observability'.
    
    --- SCORING CRITERIA ---
    1. **Technical Alignment (50%)**: How many of the JD's tools/roles are in the Resume? (Give full points for Terraform/Ansible/AWS/Production Support/GitHub Actions)
    2. **Seniority Match (30%)**: Does 'Lead' status match?
    3. **Domain Match (20%)**: Experience in industry/scale?

    Current NLP Similarity Score: {nlp_score:.2f}

    Return a JSON object with:
    - "score": A float (0.0 to 1.0) representing the total match percentage.
    - "breakdown": {{
        "technical": "Percentage",
        "seniority": "Percentage",
        "domain": "Percentage"
      }}
    - "missing_critical_keywords": ["Tool A", "Skill B"]
    - "reason": "1-sentence explanation."

    JOB DESCRIPTION:
    {job_description[:15000]}
    
    RESUME:
    {base_resume_content[:10000]}
    """
    response_text = call_llm(prompt, json_mode=True)
    try:
        cleaned = clean_json_response(response_text)
        return json.loads(cleaned)
    except Exception as e:
        # Fallback to pure NLP if AI fails
        return {
            "score": nlp_score, 
            "reason": "NLP-based estimation", 
            "breakdown": {"technical": f"{int(nlp_score*100)}%"}
        }

def tailor_resume(job_description, base_resume_content):
    prompt = f"""
    You are an AI-powered ATS Optimization Expert. Provide SPECIFIC ADDITIONS for a resume.
    
    --- BASE RESUME ---
    {base_resume_content[:10000]}
    
    --- JOB DESCRIPTION ---
    {job_description[:15000]}
    
    TASK: Identify missing keywords and responsibilities. Provide ONLY new content.
    
    RULES:
    1. Do not rewrite existing experience.
    2. Add 2-3 NEW bullets to "Lead SRE at Apple" role.
    3. Formula: [Action] + [JD Tech] + [Result].
    
    Return a JSON object with:
    - "target_job_title": "Job Title"
    - "new_apple_bullets": ["Bullet 1", "Bullet 2"]
    - "reordered_skills": {{"languages": "...", "databases": "...", "tools": "..."}}
    """
    
    response_text = call_llm(prompt, json_mode=True)
    try:
        cleaned = clean_json_response(response_text)
        additions = json.loads(cleaned)
        return merge_additions_to_resume(base_resume_content, additions)
    except Exception as e:
        logger.error(f"Tailoring failed: {e}")
        return base_resume_content

def merge_additions_to_resume(base_content, additions):
    try:
        lines = base_content.split('\n')
        new_lines = []
        target_title = additions.get("target_job_title", "").strip()
        apple_bullets = additions.get("new_apple_bullets", [])
        skills_additions = additions.get("reordered_skills", {})
        found_apple = False
        
        def clean_list(s): return [x.strip() for x in s.replace('*', '').split(',') if x.strip()]

        for line in lines:
            stripped = line.strip()
            if stripped == "**Lead SRE**" and target_title:
                new_lines.append(f"**Lead SRE | {target_title}**"); target_title = None; continue
            if "Apple" in line and ("Lead SRE" in line or "SRE" in line) and not found_apple:
                found_apple = True; new_lines.append(line)
                for b in apple_bullets:
                    bullet = b.strip().lstrip('-').strip()
                    if bullet: new_lines.append(f"- {bullet}")
                continue
            if "Languages & Scripts:" in line and skills_additions.get("languages"):
                orig = clean_list(line.split(":", 1)[1])
                new_items = clean_list(skills_additions["languages"])
                merged = ", ".join(list(dict.fromkeys(new_items + orig)))
                new_lines.append(f"- **Languages & Scripts:** {merged}"); continue
            if "Databases:" in line and skills_additions.get("databases"):
                orig = clean_list(line.split(":", 1)[1])
                new_items = clean_list(skills_additions["databases"])
                merged = ", ".join(list(dict.fromkeys(new_items + orig)))
                new_lines.append(f"- **Databases:** {merged}"); continue
            if "Tools:" in line and skills_additions.get("tools"):
                orig = clean_list(line.split(":", 1)[1])
                new_items = clean_list(skills_additions["tools"])
                merged = ", ".join(list(dict.fromkeys(new_items + orig)))
                new_lines.append(f"- **Tools:** {merged}"); continue
            new_lines.append(line)
        return '\n'.join(new_lines)
    except: return base_content
