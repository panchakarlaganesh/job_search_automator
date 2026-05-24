import os
from apify_client import ApifyClient
from dotenv import load_dotenv
from .logger import logger
from .models import JobStatus
from datetime import datetime

load_dotenv()

APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")
client = ApifyClient(APIFY_API_TOKEN) if APIFY_API_TOKEN else None

def get_dataset_id(run):
    if isinstance(run, dict):
        return run.get("defaultDatasetId")
    for attr in ["default_dataset_id", "defaultDatasetId", "default_dataset"]:
        val = getattr(run, attr, None)
        if val: return val
    try:
        return run["defaultDatasetId"]
    except:
        pass
    return None

def scrape_linkedin(keywords, locations, max_items=150):
    if not client:
        logger.error("APIFY_API_TOKEN not set")
        return []
    
    jobs = []
    for keyword in keywords:
        for location in locations:
            logger.info(f"Scraping LinkedIn for {keyword} in {location}...")
            run_input = {
                "keyword": [keyword],
                "location": location,
                "maxItems": max_items,
                "publishedAt": "r604800",
                "saveOnlyUniqueItems": True
            }
            try:
                run = client.actor("cheap_scraper/linkedin-job-scraper").call(run_input=run_input)
                dataset_id = get_dataset_id(run)
                if not dataset_id: continue

                for item in client.dataset(dataset_id).iterate_items():
                    # Validate item has minimum required data
                    ext_id = item.get('id') or item.get('jobId')
                    title = item.get('title') or item.get('jobTitle')
                    if not ext_id or not title:
                        continue # Skip invalid items

                    jobs.append({
                        "job_id_external": f"li_{ext_id}",
                        "title": title,
                        "company": item.get("companyName") or item.get("company"),
                        "location": item.get("location"),
                        "description": item.get("description") or item.get("jobDescription"),
                        "url": item.get("url") or item.get("jobUrl"),
                        "source": "linkedin",
                        "salary": item.get("salary"),
                        "posted_date": datetime.now()
                    })
            except Exception as e:
                logger.error(f"Error scraping LinkedIn: {e}")
    return jobs

def scrape_dice(keywords, locations, max_items=20):
    if not client:
        logger.error("APIFY_API_TOKEN not set")
        return []
    
    jobs = []
    for keyword in keywords:
        for location in locations:
            logger.info(f"Scraping Dice for {keyword} in {location}...")
            run_input = {
                "keyword": keyword,
                "location": location,
                "results_wanted": max_items,
                "posted_date": "7d"
            }
            try:
                run = client.actor("shahidirfan/Dice-Job-Scraper").call(run_input=run_input)
                dataset_id = get_dataset_id(run)
                if not dataset_id: continue

                for item in client.dataset(dataset_id).iterate_items():
                    ext_id = item.get('jobId') or item.get('id')
                    title = item.get('jobTitle') or item.get('title')
                    if not ext_id or not title:
                        continue

                    jobs.append({
                        "job_id_external": f"dice_{ext_id}",
                        "title": title,
                        "company": item.get("companyName") or item.get("company"),
                        "location": item.get("location"),
                        "description": item.get("description") or item.get("jobDescription"),
                        "url": item.get("jobUrl") or item.get("url"),
                        "source": "dice",
                        "salary": item.get("salary"),
                        "posted_date": datetime.now()
                    })
            except Exception as e:
                logger.error(f"Error scraping Dice: {e}")
    return jobs

def fetch_all_jobs(keywords, locations):
    all_jobs = []
    all_jobs.extend(scrape_linkedin(keywords, locations))
    all_jobs.extend(scrape_dice(keywords, locations))
    return all_jobs
