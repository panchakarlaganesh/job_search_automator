import asyncio
import random
from playwright.async_api import async_playwright
from src.logger import logger
from datetime import datetime

async def scrape_indeed_playwright(keywords, locations, max_items=10):
    jobs = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(user_agent="Mozilla/5.0", viewport={'width': 1366, 'height': 768})
        page = await context.new_page()
        for kw in keywords:
            for loc in locations:
                domain = "in.indeed.com" if loc.lower() == "india" else "www.indeed.com"
                url = f"https://{domain}/jobs?q={kw.replace(' ', '+')}&l={loc.replace(' ', '+')}&fromage=7"
                try:
                    await page.goto(url, wait_until="load", timeout=60000)
                    await asyncio.sleep(5)
                    job_links = await page.query_selector_all("a[id^='job_'], a.jcs-JobTitle")
                    for link in job_links[:max_items]:
                        title = (await link.inner_text()).strip()
                        job_url = await link.get_attribute("href")
                        jobs.append({
                            "job_id_external": f"ind_{random.randint(1000, 9999)}",
                            "title": title, "company": "Indeed Search Result",
                            "location": loc, "url": f"https://{domain}{job_url}" if not job_url.startswith("http") else job_url,
                            "source": "indeed", "description": f"Role: {title}", "posted_date": datetime.now()
                        })
                except Exception as e: logger.error(f"Indeed error: {e}")
        await browser.close()
    return jobs

async def fetch_local_jobs_async(keywords, locations):
    return await scrape_indeed_playwright(keywords, locations, 10)
