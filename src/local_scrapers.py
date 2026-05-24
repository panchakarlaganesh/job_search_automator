import asyncio
import random
from playwright.async_api import async_playwright
from .logger import logger
from datetime import datetime

async def scrape_linkedin_playwright(keywords, locations, max_items=10):
    jobs = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        for kw in keywords:
            for loc in locations:
                search_url = f"https://www.linkedin.com/jobs/search?keywords={kw.replace(' ', '%20')}&location={loc.replace(' ', '%20')}&f_TPR=r604800"
                logger.info(f"Local Scraping LinkedIn: {kw} in {loc}...")
                
                try:
                    await page.goto(search_url, wait_until="networkidle", timeout=60000)
                    await page.wait_for_selector(".base-card", timeout=15000)
                    
                    cards = await page.query_selector_all(".base-card")
                    for card in cards[:max_items]:
                        title_el = await card.query_selector(".base-search-card__title")
                        company_el = await card.query_selector(".base-search-card__subtitle")
                        location_el = await card.query_selector(".job-search-card__location")
                        link_el = await card.query_selector("a.base-card__full-link")
                        
                        if title_el and link_el:
                            title = (await title_el.inner_text()).strip()
                            company = (await company_el.inner_text()).strip() if company_el else "Unknown"
                            location = (await location_el.inner_text()).strip() if location_el else loc
                            url = await link_el.get_attribute("href")
                            job_id = url.split("?")[0].split("-")[-1] if "-" in url else str(random.randint(1000, 9999))

                            jobs.append({
                                "job_id_external": f"li_lp_{job_id}",
                                "title": title,
                                "company": company,
                                "location": location,
                                "url": url,
                                "source": "linkedin",
                                "description": f"Position: {title} at {company}. Please visit link for full details.",
                                "posted_date": datetime.now()
                            })
                except Exception as e:
                    logger.error(f"Local LinkedIn scrape error: {e}")
                
                await asyncio.sleep(random.uniform(2, 4))

        await browser.close()
    return jobs

async def scrape_indeed_playwright(keywords, locations, max_items=10):
    jobs = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        for kw in keywords:
            for loc in locations:
                search_url = f"https://www.indeed.com/jobs?q={kw.replace(' ', '+')}&l={loc.replace(' ', '+')}&fromage=7"
                logger.info(f"Local Scraping Indeed: {kw} in {loc}...")
                
                try:
                    await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
                    await page.wait_for_selector(".job_seen_beacon", timeout=15000)
                    
                    cards = await page.query_selector_all(".job_seen_beacon")
                    for card in cards[:max_items]:
                        title_el = await card.query_selector("h2.jobTitle span")
                        company_el = await card.query_selector("[data-testid='company-name']")
                        location_el = await card.query_selector("[data-testid='text-location']")
                        
                        if title_el:
                            title = (await title_el.inner_text()).strip()
                            company = (await company_el.inner_text()).strip() if company_el else "Unknown"
                            location = (await location_el.inner_text()).strip() if location_el else loc
                            
                            jobs.append({
                                "job_id_external": f"indeed_lp_{random.randint(100000, 999999)}",
                                "title": title,
                                "company": company,
                                "location": location,
                                "url": page.url,
                                "source": "indeed",
                                "description": f"Role at {company}",
                                "posted_date": datetime.now()
                            })
                except Exception as e:
                    logger.error(f"Local Indeed scrape error: {e}")
        await browser.close()
    return jobs

async def fetch_local_jobs_async(keywords, locations):
    all_jobs = []
    all_jobs.extend(await scrape_linkedin_playwright(keywords, locations, 10))
    # all_jobs.extend(await scrape_indeed_playwright(keywords, locations, 5))
    return all_jobs
