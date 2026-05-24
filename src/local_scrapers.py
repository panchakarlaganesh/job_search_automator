import asyncio
import random
from playwright.async_api import async_playwright
from .logger import logger
from datetime import datetime

async def scrape_linkedin_playwright(keywords, locations, max_items=10):
    jobs = []
    # Currently failing due to DNS/Connectivity
    return jobs

async def scrape_indeed_playwright(keywords, locations, max_items=10):
    """Indeed Scraper with more robust selectors"""
    jobs = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        for kw in keywords:
            for loc in locations:
                # Indeed India support
                domain = "in.indeed.com" if loc.lower() == "india" else "www.indeed.com"
                search_url = f"https://{domain}/jobs?q={kw.replace(' ', '+')}&l={loc.replace(' ', '+')}&fromage=7"
                logger.info(f"Local Scraping Indeed ({domain}): {kw} in {loc}...")
                
                try:
                    await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
                    # Try to handle some common overlays
                    try:
                        await page.click("button.icl-CloseButton", timeout=3000)
                    except:
                        pass

                    await page.wait_for_selector(".job_seen_beacon", timeout=15000)
                    
                    cards = await page.query_selector_all(".job_seen_beacon")
                    for card in cards[:max_items]:
                        try:
                            title_el = await card.query_selector("h2.jobTitle")
                            company_el = await card.query_selector("[data-testid='company-name']")
                            location_el = await card.query_selector("[data-testid='text-location']")
                            
                            if title_el:
                                title = (await title_el.inner_text()).strip()
                                company = (await company_el.inner_text()).strip() if company_el else "Unknown"
                                location = (await location_el.inner_text()).strip() if location_el else loc
                                
                                # Extract ID from link if possible
                                link_el = await title_el.query_selector("a")
                                job_url = f"https://{domain}" + await link_el.get_attribute("href") if link_el else page.url
                                job_id = "".join(filter(str.isalnum, job_url))[-15:] # Basic unique ID

                                jobs.append({
                                    "job_id_external": f"indeed_lp_{job_id}",
                                    "title": title,
                                    "company": company,
                                    "location": location,
                                    "url": job_url,
                                    "source": "indeed",
                                    "description": f"Role: {title} at {company} in {location}. See URL for details.",
                                    "posted_date": datetime.now()
                                })
                        except Exception as inner_e:
                            logger.error(f"Error parsing indeed card: {inner_e}")
                except Exception as e:
                    logger.error(f"Local Indeed scrape error: {e}")
                
                await asyncio.sleep(random.uniform(2, 5))
        await browser.close()
    return jobs

async def fetch_local_jobs_async(keywords, locations):
    all_jobs = []
    # LinkedIn is skipped for now due to connectivity issues
    all_jobs.extend(await scrape_indeed_playwright(keywords, locations, 10))
    return all_jobs
