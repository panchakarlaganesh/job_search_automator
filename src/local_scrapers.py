import asyncio
import random
import os
from playwright.async_api import async_playwright
from src.logger import logger
from datetime import datetime

async def scrape_indeed_playwright(keywords, locations, max_items=10):
    jobs = []
    async with async_playwright() as p:
        # Using a persistent context or more stealthy launch
        browser = await p.chromium.launch(headless=True, args=[
            "--disable-blink-features=AutomationControlled",
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ])
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"}
        )
        page = await context.new_page()
        
        for kw in keywords:
            for loc in locations:
                domain = "in.indeed.com" if loc.lower() == "india" else "www.indeed.com"
                # Randomized referral or direct navigation
                url = f"https://{domain}/jobs?q={kw.replace(' ', '+')}&l={loc.replace(' ', '+')}&fromage=7"
                try:
                    logger.info(f"Navigating to Indeed {loc}...")
                    await page.goto(url, wait_until="load", timeout=60000)
                    
                    # Human-like scroll
                    for _ in range(3):
                        await page.mouse.wheel(0, 500)
                        await asyncio.sleep(random.uniform(1, 3))

                    # Dismiss login popup
                    try:
                        await page.click("button.icl-CloseButton", timeout=3000)
                    except: pass

                    # Broader search for job cards
                    job_cards = await page.query_selector_all(".job_seen_beacon, .result, div.cardOutline")
                    logger.info(f"Found {len(job_cards)} job cards on Indeed ({loc}).")
                    
                    if not job_cards:
                        # Take debug screenshot of blocked state
                        os.makedirs("logs", exist_ok=True)
                        await page.screenshot(path=f"logs/blocked_{loc}.png")
                        if "Blocked" in await page.title():
                            logger.error(f"Indeed blocked the request for {loc}.")
                            continue

                    # Use a set to track unique URLs for this run
                    seen_urls = set()
                    for card in job_cards[:max_items * 2]: # Scan a bit more to allow for duplicates
                        if len(jobs) >= max_items: break
                        
                        # Try multiple title selectors
                        title_elem = await card.query_selector("h2.jobTitle span, a.jcs-JobTitle, .jobTitle")
                        title = (await title_elem.inner_text()).strip() if title_elem else "Unknown Title"
                        
                        company_elem = await card.query_selector("[data-testid='company-name'], .companyName, .provider")
                        company = (await company_elem.inner_text()).strip() if company_elem else "Unknown Company"
                        
                        link_elem = await card.query_selector("h2.jobTitle a, a.jcs-JobTitle")
                        job_url_rel = await link_elem.get_attribute("href") if link_elem else ""
                        job_url = f"https://{domain}{job_url_rel}" if job_url_rel and not job_url_rel.startswith("http") else job_url_rel
                        
                        # Deduplicate
                        if job_url in seen_urls: continue
                        seen_urls.add(job_url)

                        snippet_elem = await card.query_selector(".job-snippet, .summary")
                        desc = (await snippet_elem.inner_text()).strip() if snippet_elem else f"Role at {company}"
                        
                        jobs.append({
                            "job_id_external": f"ind_{random.randint(100000, 999999)}",
                            "title": title,
                            "company": company,
                            "location": loc,
                            "url": job_url,
                            "source": "indeed",
                            "description": desc,
                            "posted_date": datetime.now()
                        })
                except Exception as e:
                    logger.error(f"Indeed scraper failed for {loc}: {e}")
                    
        await browser.close()
    return jobs

async def fetch_local_jobs_async(keywords, locations):
    return await scrape_indeed_playwright(keywords, locations, 10)
