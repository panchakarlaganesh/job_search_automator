import asyncio
import random
from playwright.async_api import async_playwright
from .logger import logger
from datetime import datetime

async def scrape_indeed_playwright(keywords, locations, max_items=10):
    """Headful Indeed Scraper to handle Cloudflare/Captchas manually if needed"""
    jobs = []
    async with async_playwright() as p:
        # Launching HEADFUL so you can see it and solve captchas if they appear
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        # Give a small hint to user
        logger.info("Starting headful browser. If a captcha appears, please solve it in the window!")

        for kw in keywords:
            for loc in locations:
                domain = "in.indeed.com" if loc.lower() == "india" else "www.indeed.com"
                search_url = f"https://{domain}/jobs?q={kw.replace(' ', '+')}&l={loc.replace(' ', '+')}&fromage=7"
                logger.info(f"Local Headful Scraping Indeed: {kw} in {loc}...")
                
                try:
                    # Longer timeout for manual intervention if needed
                    await page.goto(search_url, wait_until="load", timeout=120000)
                    
                    # Wait for either job cards or a captcha
                    await asyncio.sleep(5) # Give it time to render

                    selectors = [".job_seen_beacon", ".result", "[data-testid='jobListing']"]
                    found_selector = None
                    for s in selectors:
                        try:
                            await page.wait_for_selector(s, timeout=10000)
                            found_selector = s
                            break
                        except:
                            continue
                    
                    if not found_selector:
                        logger.warning(f"No job cards found. Please check the browser window.")
                        await asyncio.sleep(10) # Wait for user to maybe solve captcha
                        # Try one more time
                        for s in selectors:
                            try:
                                await page.wait_for_selector(s, timeout=5000)
                                found_selector = s
                                break
                            except:
                                continue

                    if found_selector:
                        cards = await page.query_selector_all(found_selector)
                        logger.info(f"Found {len(cards)} potential jobs.")

                        for card in cards[:max_items]:
                            try:
                                title_el = await card.query_selector("h2.jobTitle, .jobTitle")
                                company_el = await card.query_selector("[data-testid='company-name'], .companyName")
                                location_el = await card.query_selector("[data-testid='text-location'], .companyLocation")
                                
                                if title_el:
                                    title = (await title_el.inner_text()).strip()
                                    company = (await company_el.inner_text()).strip() if company_el else "Unknown"
                                    location = (await location_el.inner_text()).strip() if location_el else loc
                                    
                                    job_id = f"{title}_{company}_{location}".replace(" ", "")[:30]

                                    jobs.append({
                                        "job_id_external": f"indeed_hf_{job_id}_{random.randint(100, 999)}",
                                        "title": title,
                                        "company": company,
                                        "location": location,
                                        "url": page.url,
                                        "source": "indeed",
                                        "description": f"Role: {title} at {company}. Scraped via headful local agent.",
                                        "posted_date": datetime.now()
                                    })
                            except Exception as inner_e:
                                logger.error(f"Card parse error: {inner_e}")
                            
                except Exception as e:
                    logger.error(f"Local Indeed headful error: {e}")
                
                await asyncio.sleep(random.uniform(5, 8))
        await browser.close()
    return jobs

async def fetch_local_jobs_async(keywords, locations):
    all_jobs = []
    all_jobs.extend(await scrape_indeed_playwright(keywords, locations, 10))
    return all_jobs
