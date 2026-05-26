import os
from apify_client import ApifyClient
from src.logger import logger

def fetch_all_jobs(keywords, locations, max_items=150):
    """
    Fetches job listings from LinkedIn using Apify's cheap_scraper/linkedin-job-scraper.
    """
    api_token = os.getenv("APIFY_API_TOKEN")
    if not api_token:
        logger.error("APIFY_API_TOKEN not found in environment variables.")
        return []

    client = ApifyClient(api_token)
    
    all_jobs = []
    
    # The actor supports multiple keywords, but we'll loop through locations 
    # if there are multiple, as the actor typically handles one location string.
    for location in locations:
        run_input = {
            "keyword": keywords,
            "location": location,
            "maxItems": max_items,
            "publishedAt": "r604800", # Past week
            "saveOnlyUniqueItems": True,
            "enrichCompanyData": False # Faster
        }

        try:
            logger.info(f"Running Apify LinkedIn scraper for keywords {keywords} in {location}...")
            # Run the Actor and wait for it to finish
            run = client.actor("cheap_scraper/linkedin-job-scraper").call(run_input=run_input)

            # Fetch results from the run's dataset
            for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                # Map Apify item to our Job model format
                job_data = {
                    "job_id_external": str(item.get("id", item.get("jobId"))),
                    "title": item.get("title"),
                    "company": item.get("companyName"),
                    "location": item.get("location"),
                    "url": item.get("url"),
                    "description": item.get("description"),
                    "source": "linkedin",
                    "posted_at": item.get("postedAt")
                }
                
                # Basic validation
                if job_data["job_id_external"] and job_data["title"]:
                    all_jobs.append(job_data)
                    
            logger.info(f"Fetched {len(all_jobs)} jobs from LinkedIn for {location}.")
            
        except Exception as e:
            logger.error(f"Apify LinkedIn scraper failed for {location}: {e}")

    return all_jobs
