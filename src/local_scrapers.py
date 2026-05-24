import asyncio
import random
from playwright.async_api import async_playwright
from .logger import logger
from datetime import datetime

async def scrape_indeed_playwright(keywords, locations, max_items=10):
    """
    Indeed Scraper using a search-by-URL approach which is often more stable.
    """
    jobs = []
    async with async_playwright() as p:
        # Launching with specific arguments to reduce bot detection
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1366, 'height': 768}
        )
        page = await context.new_page()
        
        for kw in keywords:
            for loc in locations:
                domain = "in.indeed.com" if loc.lower() == "india" else "www.indeed.com"
                # Updated search URL format
                search_url = f"https://{domain}/jobs?q={kw.replace(' ', '+')}&l={loc.replace(' ', '+')}&fromage=7"
                logger.info(f"Navigating to Indeed Search: {search_url}")
                
                try:
                    await page.goto(search_url, wait_until="load", timeout=90000)
                    await asyncio.sleep(7) # Wait for Cloudflare/Loaders

                    # Indeed often uses 'Mosaic' layout. Let's look for the main container.
                    await page.wait_for_selector("#mosaic-provider-jobcards", timeout=20000)
                    
                    # More generic selector for job links which usually contain the title
                    job_links = await page.query_selector_all("a[id^='job_'], a.jcs-JobTitle")
                    logger.info(f"Found {len(job_links)} job title links.")

                    for link in job_links[:max_items]:
                        try:
                            # Scroll link into view to trigger lazy loading
                            await link.scroll_into_view_if_needed()
                            
                            title = (await link.inner_text()).strip()
                            
                            # Navigate to company and location from parent container
                            container = await page.evaluate_handle("(el) => el.closest('.job_seen_beacon') || el.parentElement.parentElement", link)
                            
                            company = "Unknown"
                            location = loc
                            
                            if container:
                                company_el = await container.query_selector("[data-testid='company-name']")
                                if company_el:
                                    company = (await company_el.inner_text()).strip()
                                
                                loc_el = await container.query_selector("[data-testid='text-location']")
                                if loc_el:
                                    location = (await loc_el.inner_text()).strip()

                            job_id = f"ind_{random.randint(10000, 99999)}"
                            url = await link.get_attribute("href")
                            if url and not url.startswith("http"):
                                url = f"https://{domain}{url}"

                            jobs.append({
                                "job_id_external": f"indeed_gen_{job_id}",
                                "title": title,
                                "company": company,
                                "location": location,
                                "url": url,
                                "source": "indeed",
                                "description": f"Role: {title} at {company}. Scraped via stable-link agent.",
                                "posted_date": datetime.now()
                            })
                        except Exception as inner_e:
                            logger.error(f"Link parse error: {inner_e}")
                            
                except Exception as e:
                    logger.error(f"Local Indeed stable-link error: {e}")
                    await page.screenshot(path="logs/indeed_debug.png")
                
                await asyncio.sleep(random.uniform(5, 10))
        await browser.close()
    return jobs

async def fetch_local_jobs_async(keywords, locations):
    return await scrape_indeed_playwright(keywords, locations, 10)
