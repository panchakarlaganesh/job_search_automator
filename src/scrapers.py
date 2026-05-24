import os
from apify_client import ApifyClient
from dotenv import load_dotenv
from .logger import logger
from .models import JobStatus
from datetime import datetime

load_dotenv()

APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")
client = ApifyClient(APIFY_API_TOKEN) if APIFY_API_TOKEN else None

def scrape_linkedin(keywords, locations, max_items=50):
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
                "publishedAt": "r604800", # Last 7 days
                "saveOnlyUniqueItems": True
            }
            try:
                run = client.actor("cheap_scraper/linkedin-job-scraper").call(run_input=run_input)
                for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                    jobs.append({
                        "job_id_external": f"li_{item.get('id')}",
                        "title": item.get("title"),
                        "company": item.get("companyName"),
                        "location": item.get("location"),
                        "description": item.get("description"),
                        "url": item.get("url"),
                        "source": "linkedin",
                        "salary": item.get("salary"),
                        "posted_date": datetime.now() # Simplified for now
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
                for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                    jobs.append({
                        "job_id_external": f"dice_{item.get('jobId')}",
                        "title": item.get("jobTitle"),
                        "company": item.get("companyName"),
                        "location": item.get("location"),
                        "description": item.get("description"),
                        "url": item.get("jobUrl"),
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
