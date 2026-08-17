import re
import html
import random
import time
import requests
from datetime import datetime
from src.logger import logger
from src.job_utils import stable_job_id, normalize_job_url

SEARCH_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
DETAIL_URL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting"

# Honest self-identifying User-Agent (upstream fix da12d6e).
# Spoofed browser UAs violate LinkedIn's ToS and are more likely to be blocked.
USER_AGENT = "Mozilla/5.0 (compatible; linkedin-search-cli/1.0)"

def clean_html(text):
    if not text:
        return ""
    # Strip HTML tags
    cleaned = re.sub(r'<[^>]+>', ' ', text)
    # Decode HTML entities
    cleaned = html.unescape(cleaned)
    # Normalize whitespaces
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned.strip()

def extract_div_content(html_content, class_name):
    escaped = re.escape(class_name)
    open_re = re.compile(rf'<div[^>]*class="[^"]*{escaped}[^"]*"[^>]*>', re.IGNORECASE)
    match = open_re.search(html_content)
    if not match:
        return None

    i = match.end()
    depth = 1
    
    while depth > 0 and i < len(html_content):
        next_open = html_content.find('<div', i)
        next_close = html_content.find('</div>', i)
        
        if next_close == -1:
            return None
            
        if next_open != -1 and next_open < next_close:
            depth += 1
            i = next_open + 4
        else:
            depth -= 1
            i = next_close + 6
            
    return html_content[match.end():i-6]

def http_get(url, params=None):
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    max_retries = 5
    delay = 1.0
    for attempt in range(max_retries + 1):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=15)
            if response.status_code == 429 or response.status_code >= 500:
                if attempt == max_retries:
                    logger.error(f"HTTP request failed with status {response.status_code}")
                    return None
                jitter = random.uniform(0, 0.5)
                time.sleep(delay + jitter)
                delay = min(delay * 2, 8.0)
                continue
            if response.status_code == 404:
                return ""
            if response.status_code != 200:
                logger.error(f"HTTP request failed with status {response.status_code}")
                return None
            return response.text
        except Exception as e:
            if attempt == max_retries:
                logger.error(f"HTTP request exception: {e}")
                return None
            time.sleep(delay)
            delay = min(delay * 2, 8.0)
    return None

def fetch_linkedin_guest_jobs(keywords, locations, max_items=150, days_back=7, jobage_minutes=None):
    """
    Fetches jobs from LinkedIn Guest Search API (zero API key/Playwright requirement).

    Args:
        jobage_minutes: If set, overrides days_back for sub-day freshness filtering
                        (upstream fix b167efa). E.g. jobage_minutes=90 returns jobs
                        posted in the last 90 minutes. Cannot be combined with days_back.
    """
    if jobage_minutes is not None and days_back != 7:
        raise ValueError("jobage_minutes and days_back are mutually exclusive. Use one or the other.")

    all_jobs = []

    # Translate freshness preference to LinkedIn f_TPR format (seconds)
    if jobage_minutes is not None:
        tpr = f"r{jobage_minutes * 60}"  # sub-day precision (upstream b167efa)
    elif days_back:
        tpr = f"r{days_back * 86400}"
    else:
        tpr = None
    
    for kw in keywords:
        for loc in locations:
            logger.info(f"LinkedIn Guest Search: Querying '{kw}' in '{loc}' (last {days_back} days)...")
            page = 0
            retrieved_count = 0
            
            while retrieved_count < max_items:
                params = {
                    "keywords": kw,
                    "location": loc,
                    "start": page * 10
                }
                if tpr:
                    params["f_TPR"] = tpr
                    
                html_res = http_get(SEARCH_URL, params=params)
                if not html_res:
                    break
                
                chunks = html_res.split('data-entity-urn="urn:li:jobPosting:')[1:]
                if not chunks:
                    logger.info("LinkedIn Guest Search: No more jobs returned.")
                    break
                    
                cards_on_page = 0
                for chunk in chunks:
                    if retrieved_count >= max_items:
                        break
                        
                    id_match = re.match(r'^(\d+)', chunk)
                    if not id_match:
                        continue
                    job_id = id_match.group(1)
                    
                    link_match = re.search(r'class="base-card__full-link[^"]*"[^>]*href="([^"]+)"', chunk, re.IGNORECASE)
                    job_url = link_match.group(1).split("?")[0] if link_match else f"https://www.linkedin.com/jobs/view/{job_id}"
                    
                    title = ""
                    h3_match = re.search(r'class="base-search-card__title"[^>]*>([\s\S]*?)<\/h3>', chunk, re.IGNORECASE)
                    if h3_match:
                        title = clean_html(h3_match.group(1))
                    if not title:
                        sr_match = re.search(r'class="sr-only"[^>]*>([\s\S]*?)<\/span>', chunk, re.IGNORECASE)
                        if sr_match:
                            title = clean_html(sr_match.group(1))
                            
                    if not title:
                        continue
                        
                    company = "Unknown"
                    sub_match = re.search(r'class="base-search-card__subtitle"[^>]*>([\s\S]*?)<\/h4>', chunk, re.IGNORECASE)
                    if sub_match:
                        company = clean_html(sub_match.group(1))
                        
                    loc_match = re.search(r'class="job-search-card__location"[^>]*>([\s\S]*?)<\/span>', chunk, re.IGNORECASE)
                    job_loc = clean_html(loc_match.group(1)) if loc_match else loc
                    
                    # Store a temporary placeholder description until detail is fetched
                    job_data = {
                        "job_id_external": job_id,
                        "title": title,
                        "company": company,
                        "location": job_loc,
                        "url": job_url,
                        "description": "",
                        "source": "linkedin_guest",
                        "posted_date": datetime.utcnow()
                    }
                    
                    all_jobs.append(job_data)
                    cards_on_page += 1
                    retrieved_count += 1
                
                if cards_on_page == 0:
                    break
                    
                page += 1
                # Sleep a tiny bit to respect rate limits
                time.sleep(random.uniform(0.5, 1.2))
                
    # Now, let's fetch detail description for the scraped jobs
    logger.info(f"LinkedIn Guest Search: Fetching detail page for {len(all_jobs)} jobs...")
    enriched_jobs = []

    # CSS class selectors to try in order — LinkedIn updates markup periodically
    DESC_SELECTORS = [
        "show-more-less-html__markup",
        "description__text",
        "decorated-job-posting__details",
        "jobs-description-content__text",
        "job-view-layout",
    ]

    for i, job in enumerate(all_jobs):
        job_id = job["job_id_external"]
        detail_url = f"{DETAIL_URL}/{job_id}"

        detail_html = http_get(detail_url)

        # Always keep the job card regardless of whether detail fetch succeeded.
        # If detail is unavailable the job is stored with an empty description
        # and main.py will skip scoring but still persist it for future enrichment.
        if detail_html:
            # Try each known selector in order
            desc_html = None
            for selector in DESC_SELECTORS:
                desc_html = extract_div_content(detail_html, selector)
                if desc_html:
                    break

            if desc_html:
                with_breaks = re.sub(r'<\s*br\s*\/?>', '\n', desc_html, flags=re.IGNORECASE)
                with_breaks = re.sub(r'<\/(p|li|ul|ol|div|h\d)>', '\n', with_breaks, flags=re.IGNORECASE)
                description = clean_html(with_breaks)
                description = re.sub(r'\n{3,}', '\n\n', description).strip()
                if description:
                    job["description"] = description
            else:
                # Last-resort: strip all HTML and take whatever plain text remains
                plain = clean_html(detail_html)
                plain = re.sub(r'\s{4,}', '\n\n', plain).strip()
                if len(plain) > 200:
                    job["description"] = plain[:8000]  # cap to avoid huge blobs
                    logger.debug(f"Used plain-text fallback for job {job_id}")

        enriched_jobs.append(job)
        time.sleep(random.uniform(0.5, 1.0))

    desc_count = sum(1 for j in enriched_jobs if len(j.get("description", "")) > 200)
    logger.info(f"LinkedIn Guest Search: {len(enriched_jobs)} jobs kept, {desc_count} with full descriptions.")
    return enriched_jobs
