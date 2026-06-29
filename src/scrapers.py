import os
from apify_client import ApifyClient
from src.logger import logger
from src.job_utils import stable_job_id

def fetch_all_jobs(keywords, locations, max_items=150, days_back=3):
    """
    Fetches job listings from LinkedIn using Apify's cheap_scraper/linkedin-job-scraper.
    """
    api_token = os.getenv("APIFY_API_TOKEN") or os.getenv("APIFY_TOKEN")
    if not api_token:
        logger.error("APIFY_API_TOKEN or APIFY_TOKEN not found in environment variables.")
        return []

    client = ApifyClient(api_token)
    all_jobs = []

    # Map days_back to Apify's allowed publishedAt values
    # Allowed: "" (any), "r86400" (1 day), "r604800" (7 days), "r2592000" (30 days)
    if days_back <= 1:
        published_at = "r86400"
    elif days_back <= 7:
        published_at = "r604800"
    elif days_back <= 30:
        published_at = "r2592000"
    else:
        published_at = ""
    
    # Convert keywords to list if they aren't already, as cheap_scraper expects an array
    keyword_list = keywords if isinstance(keywords, list) else [keywords]

    for location in locations:
        run_input = {
            "keyword": keyword_list,
            "location": location,
            "maxItems": max(150, max_items),  # cheap_scraper requires maxItems >= 150
            "publishedAt": published_at,
            "saveOnlyUniqueItems": True,
            "enrichCompanyData": False
        }

        try:
            logger.info(f"Running Apify LinkedIn scraper for keywords {keyword_list} in {location}...")
            # Run the Actor and wait for it to finish
            run = client.actor("cheap_scraper/linkedin-job-scraper").call(run_input=run_input)

            # Fetch results from the run's dataset
            dataset_id = run.get("defaultDatasetId") if isinstance(run, dict) else getattr(run, "default_dataset_id", None)
            for item in client.dataset(dataset_id).iterate_items():
                # Map Apify item to our Job model format
                job_id = str(item.get("id", item.get("jobId", "")))
                job_url = item.get("url")
                title = item.get("title")
                company = item.get("companyName")
                job_data = {
                    "job_id_external": job_id if job_id else stable_job_id("linkedin", job_url, title or "", company or ""),
                    "title": title,
                    "company": company,
                    "location": item.get("location"),
                    "url": job_url,
                    "description": item.get("description"),
                    "source": "linkedin",
                    "posted_at": item.get("postedAt")
                }

                # Basic validation
                if job_data["title"]:
                    all_jobs.append(job_data)

            logger.info(f"Fetched {len(all_jobs)} jobs from LinkedIn for {location}.")

        except Exception as e:
            logger.error(f"Apify LinkedIn scraper failed for {location}: {e}")

    return all_jobs


def fetch_naukri_jobs(keywords, locations, max_items=150):
    """
    Fetches job listings from Naukri.com using Apify's moving_beacon-owner1/naukri-jobs-scraper.
    """
    api_token = os.getenv("APIFY_API_TOKEN") or os.getenv("APIFY_TOKEN")
    if not api_token:
        logger.error("APIFY_API_TOKEN or APIFY_TOKEN not found in environment variables.")
        return []

    client = ApifyClient(api_token)
    all_jobs = []

    keyword_list = keywords if isinstance(keywords, list) else [keywords]
    
    # Filter locations to find India-related targets
    # For Naukri, general "India" should be empty (searches all India). Specific cities (e.g. bangalore) are passed.
    india_locations = []
    has_general_india = False
    india_cities = ["bangalore", "delhi", "mumbai", "hyderabad", "pune", "chennai", "kolkata", "noida", "gurgaon"]
    
    for loc in locations:
        loc_lower = loc.lower()
        if "india" in loc_lower:
            has_general_india = True
        
        # Check if any specific Indian city matches
        found_cities = [city for city in india_cities if city in loc_lower]
        if found_cities:
            india_locations.append(found_cities[0])
            
    # If "India" general is requested, or no specific Indian locations are found, query all India (empty string)
    if has_general_india or not india_locations:
        if "" not in india_locations:
            india_locations.append("")

    for keyword in keyword_list:
        for loc in india_locations:
            run_input = {
                "searchKeyword": keyword,
                "maxPages": 3,
                "maxItems": max(50, max_items // len(india_locations)),
                "backend": "render",
                "respectRobots": False,
                "proxyConfiguration": {"useApifyProxy": True}
            }
            if loc:
                run_input["location"] = loc

            try:
                logger.info(f"Running Apify Naukri scraper for keyword '{keyword}' in '{loc or 'All India'}'...")
                run = client.actor("moving_beacon-owner1/naukri-jobs-scraper").call(run_input=run_input)
                dataset_id = run.get("defaultDatasetId") if isinstance(run, dict) else getattr(run, "default_dataset_id", None)
                
                count = 0
                for item in client.dataset(dataset_id).iterate_items():
                    job_url = item.get("url")
                    title = item.get("title")
                    company = item.get("companyName") or item.get("company")
                    job_id = str(item.get("id") or item.get("jobId") or "")
                    
                    # Fallback descriptions
                    description = item.get("descriptionSnippet") or item.get("description") or ""
                    
                    job_data = {
                        "job_id_external": job_id if job_id else stable_job_id("naukri", job_url, title or "", company or ""),
                        "title": title,
                        "company": company,
                        "location": item.get("location") or loc or "India",
                        "url": job_url,
                        "description": description,
                        "source": "naukri",
                        "posted_at": item.get("postedDate") or item.get("postedAt")
                    }

                    if job_data["title"]:
                        all_jobs.append(job_data)
                        count += 1

                logger.info(f"Fetched {count} jobs from Naukri for keyword '{keyword}' in '{loc or 'All India'}'.")

            except Exception as e:
                logger.error(f"Apify Naukri scraper failed for '{keyword}' in '{loc}': {e}")

    return all_jobs
