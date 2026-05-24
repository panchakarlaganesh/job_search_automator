import asyncio
import random
from playwright.async_api import async_playwright
from .logger import logger
from datetime import datetime

async def scrape_indeed_playwright(keywords, locations, max_items=10):
    """Enhanced stealth Indeed Scraper"""
    jobs = []
    async with async_playwright() as p:
        # Launching with more "human" defaults
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        for kw in keywords:
            for loc in locations:
                domain = "in.indeed.com" if loc.lower() == "india" else "www.indeed.com"
                search_url = f"https://{domain}/jobs?q={kw.replace(' ', '+')}&l={loc.replace(' ', '+')}&fromage=7"
                logger.info(f"Local Stealth Scraping Indeed: {kw} in {loc}...")
                
                try:
                    await page.goto(search_url, wait_until="networkidle", timeout=60000)
                    
                    # Scroll to mimic human
                    for _ in range(3):
                        await page.mouse.wheel(0, 500)
                        await asyncio.sleep(random.uniform(0.5, 1.5))

                    # Indeed often uses different layouts. Let's try multiple selectors.
                    selectors = [".job_seen_beacon", ".result", "[data-testid='jobListing']"]
                    found_selector = None
                    for s in selectors:
                        try:
                            await page.wait_for_selector(s, timeout=5000)
                            found_selector = s
                            break
                        except:
                            continue
                    
                    if not found_selector:
                        # Take a screenshot for debugging if it fails
                        logger.warning(f"No job cards found on {domain}. Anti-bot might be triggered.")
                        await page.screenshot(path=f"logs/indeed_fail_{domain}.png")
                        continue

                    cards = await page.query_selector_all(found_selector)
                    logger.info(f"Found {len(cards)} potential jobs on {domain}.")

                    for card in cards[:max_items]:
                        try:
                            # Try multiple title selectors
                            title_el = await card.query_selector("h2.jobTitle, .jobTitle, [id^='job_']")
                            company_el = await card.query_selector("[data-testid='company-name'], .companyName")
                            location_el = await card.query_selector("[data-testid='text-location'], .companyLocation")
                            
                            if title_el:
                                title = (await title_el.inner_text()).strip()
                                company = (await company_el.inner_text()).strip() if company_el else "Unknown"
                                location = (await location_el.inner_text()).strip() if location_el else loc
                                
                                # Use a stable hash-like ID for deduplication
                                job_id = f"{title}_{company}_{location}".replace(" ", "")[:30]

                                jobs.append({
                                    "job_id_external": f"indeed_st_{job_id}_{random.randint(100, 999)}",
                                    "title": title,
                                    "company": company,
                                    "location": location,
                                    "url": page.url, # URL extraction from cards is complex on Indeed due to redirects
                                    "source": "indeed",
                                    "description": f"Role: {title} at {company}. Scraped via stealth local agent.",
                                    "posted_date": datetime.now()
                                })
                        except Exception as inner_e:
                            logger.error(f"Card parse error: {inner_e}")
                            
                except Exception as e:
                    logger.error(f"Local Indeed stealth error: {e}")
                
                await asyncio.sleep(random.uniform(5, 10))
        await browser.close()
    return jobs

async def fetch_local_jobs_async(keywords, locations):
    all_jobs = []
    all_jobs.extend(await scrape_indeed_playwright(keywords, locations, 10))
    return all_jobs
