import asyncio
import random
import os
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
from src.logger import logger
from datetime import datetime

# --- Browser Utilities ---

async def get_stealth_browser(p):
    return await p.chromium.launch(headless=True, args=[
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-infobars",
        "--window-position=0,0",
        "--ignore-certifcate-errors",
        "--ignore-certifcate-errors-spki-list",
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ])

async def get_stealth_context(browser):
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        viewport={'width': 1920, 'height': 1080}
    )
    return context

async def apply_stealth(page):
    await stealth_async(page)

async def human_scroll(page):
    for _ in range(random.randint(1, 3)):
        await page.mouse.wheel(0, random.randint(300, 600))
        await asyncio.sleep(random.uniform(1, 2))

async def fetch_full_description(page, url, selector):
    """Deep Scrapes the full job description from a detail page."""
    try:
        await page.goto(url, wait_until="load", timeout=30000)
        await asyncio.sleep(2)
        desc_elem = await page.query_selector(selector)
        if desc_elem:
            return (await desc_elem.inner_text()).strip()
    except Exception as e:
        logger.debug(f"Deep scrape failed for {url}: {e}")
    return None

# --- Individual Scrapers ---

async def scrape_indeed(keywords, locations, max_items, days_back):
    jobs = []
    async with async_playwright() as p:
        browser = await get_stealth_browser(p)
        context = await get_stealth_context(browser)
        page = await context.new_page()
        await apply_stealth(page)
        for kw in keywords:
            for loc in locations:
                domain = "in.indeed.com" if loc.lower() == "india" else "www.indeed.com"
                url = f"https://{domain}/jobs?q={kw.replace(' ', '+')}&l={loc.replace(' ', '+')}&fromage={days_back}"
                try:
                    logger.info(f"Indeed: Searching {kw} in {loc}...")
                    await page.goto(url, wait_until="load")
                    await human_scroll(page)
                    cards = await page.query_selector_all(".job_seen_beacon, li.css-5lfssm, .result")
                    for card in cards[:max_items]:
                        title_el = await card.query_selector("h2.jobTitle, [data-testid='jobTitle']")
                        company_el = await card.query_selector("[data-testid='company-name'], .companyName")
                        link_el = await card.query_selector("a[data-jk], h2.jobTitle a")
                        if title_el and link_el:
                            title = (await title_el.inner_text()).strip()
                            company = (await company_el.inner_text()).strip() if company_el else "Unknown"
                            href = await link_el.get_attribute("href")
                            job_url = f"https://{domain}{href}" if href and not href.startswith("http") else href
                            jobs.append({
                                "job_id_external": f"ind_{href.split('jk=')[-1][:16]}" if "jk=" in href else f"ind_{os.urandom(4).hex()}",
                                "title": title, "company": company, "location": loc, "url": job_url,
                                "source": "indeed", "description": f"Indeed: {title} @ {company}", "posted_date": datetime.now()
                            })
                except Exception as e: logger.error(f"Indeed Error: {e}")
        await browser.close()
    return jobs

async def scrape_dice(keywords, locations, max_items, days_back):
    jobs = []
    async with async_playwright() as p:
        browser = await get_stealth_browser(p)
        context = await get_stealth_context(browser)
        page = await context.new_page()
        await apply_stealth(page)
        for kw in keywords:
            for loc in locations:
                url = f"https://www.dice.com/jobs?q={kw.replace(' ', '%20')}&location={loc.replace(' ', '%20')}&pageSize=20&postedDate={days_back}"
                try:
                    logger.info(f"Dice: Searching {kw} in {loc}...")
                    await page.goto(url, wait_until="load")
                    await asyncio.sleep(5)
                    cards = await page.query_selector_all("[data-testid='job-card'], .card")
                    for card in cards[:max_items]:
                        title_el = await card.query_selector("[data-testid='job-title-link'], .title")
                        company_el = await card.query_selector("[data-testid='company-name'], .company")
                        if title_el:
                            title = (await title_el.inner_text()).strip()
                            company = (await company_el.inner_text()).strip() if company_el else "Unknown"
                            href = await title_el.get_attribute("href")
                            job_url = href if href.startswith("http") else f"https://www.dice.com{href}"
                            jobs.append({
                                "job_id_external": f"dice_{os.urandom(4).hex()}",
                                "title": title, "company": company, "location": loc, "url": job_url,
                                "source": "dice", "description": f"Dice: {title} @ {company}", "posted_date": datetime.now()
                            })
                except Exception as e: logger.error(f"Dice Error: {e}")
        await browser.close()
    return jobs

async def scrape_linkedin(keywords, locations, max_items, days_back):
    jobs = []
    async with async_playwright() as p:
        browser = await get_stealth_browser(p)
        context = await get_stealth_context(browser)
        page = await context.new_page()
        await apply_stealth(page)
        time_map = {1: "r86400", 2: "r172800", 3: "r259200", 7: "r604800"}
        f_tpr = time_map.get(days_back, "r604800")
        for kw in keywords:
            for loc in locations:
                url = f"https://www.linkedin.com/jobs/search/?keywords={kw.replace(' ', '%20')}&location={loc.replace(' ', '%20')}&f_TPR={f_tpr}"
                try:
                    logger.info(f"LinkedIn: Searching {kw} in {loc}...")
                    await page.goto(url, wait_until="load")
                    await asyncio.sleep(3)
                    cards = await page.query_selector_all(".base-card, .job-search-card")
                    for card in cards[:max_items]:
                        title_el = await card.query_selector(".base-search-card__title, h3")
                        link_el = await card.query_selector("a.base-card__full-link, a")
                        if title_el and link_el:
                            title = (await title_el.inner_text()).strip()
                            job_url = (await link_el.get_attribute("href")).split('?')[0]
                            jobs.append({
                                "job_id_external": f"li_{os.urandom(4).hex()}",
                                "title": title, "company": "LinkedIn", "location": loc, "url": job_url,
                                "source": "linkedin", "description": f"LinkedIn: {title}", "posted_date": datetime.now()
                            })
                except Exception as e: logger.error(f"LinkedIn Error: {e}")
        await browser.close()
    return jobs

async def scrape_ziprecruiter(keywords, locations, max_items, days_back):
    jobs = []
    async with async_playwright() as p:
        browser = await get_stealth_browser(p)
        context = await get_stealth_context(browser)
        page = await context.new_page()
        await apply_stealth(page)
        for kw in keywords:
            for loc in locations:
                url = f"https://www.ziprecruiter.com/jobs-search?search={kw.replace(' ', '+')}&location={loc.replace(' ', '+')}&days={days_back}"
                try:
                    logger.info(f"ZipRecruiter: Searching {kw} in {loc}...")
                    await page.goto(url, wait_until="load")
                    cards = await page.query_selector_all(".job_content, .job_result")
                    for card in cards[:max_items]:
                        title_el = await card.query_selector(".job_title, h2")
                        link_el = await card.query_selector("a.job_link, a")
                        if title_el and link_el:
                            title = (await title_el.inner_text()).strip()
                            job_url = await link_el.get_attribute("href")
                            jobs.append({
                                "job_id_external": f"zr_{os.urandom(4).hex()}",
                                "title": title, "company": "ZipRecruiter", "location": loc, "url": job_url,
                                "source": "ziprecruiter", "description": f"ZipRecruiter: {title}", "posted_date": datetime.now()
                            })
                except Exception as e: logger.error(f"ZipRecruiter Error: {e}")
        await browser.close()
    return jobs

async def scrape_glassdoor(keywords, locations, max_items, days_back):
    jobs = []
    async with async_playwright() as p:
        browser = await get_stealth_browser(p)
        context = await get_stealth_context(browser)
        page = await context.new_page()
        await apply_stealth(page)
        for kw in keywords:
            for loc in locations:
                url = f"https://www.glassdoor.com/Job/jobs.htm?sc.keyword={kw.replace(' ', '+')}&locT=C&locP={loc.replace(' ', '+')}&fromAge={days_back}"
                try:
                    logger.info(f"Glassdoor: Searching {kw} in {loc}...")
                    await page.goto(url, wait_until="load")
                    await asyncio.sleep(4)
                    cards = await page.query_selector_all("[data-test='job-listing']")
                    for card in cards[:max_items]:
                        title_el = await card.query_selector("[data-test='job-title']")
                        if title_el:
                            title = (await title_el.inner_text()).strip()
                            href = await title_el.get_attribute("href")
                            job_url = f"https://www.glassdoor.com{href}" if not href.startswith("http") else href
                            jobs.append({
                                "job_id_external": f"gd_{os.urandom(4).hex()}",
                                "title": title, "company": "Glassdoor", "location": loc, "url": job_url,
                                "source": "glassdoor", "description": f"Glassdoor: {title}", "posted_date": datetime.now()
                            })
                except Exception as e: logger.error(f"Glassdoor Error: {e}")
        await browser.close()
    return jobs

# --- Main Entry Point (Parallel) ---

async def fetch_local_jobs_async(keywords, locations, days_back=3):
    """Runs all scrapers in parallel with isolated browser sessions."""
    logger.info("Starting Parallel Multi-Board Search...")
    
    tasks = [
        scrape_indeed(keywords, locations, 10, days_back),
        scrape_dice(keywords, locations, 10, days_back),
        scrape_linkedin(keywords, locations, 10, days_back),
        scrape_ziprecruiter(keywords, locations, 10, days_back),
        scrape_glassdoor(keywords, locations, 10, days_back)
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    combined_jobs = []
    for res in results:
        if isinstance(res, list): combined_jobs.extend(res)
        elif isinstance(res, Exception): logger.error(f"Scraper task failed: {res}")
            
    logger.info(f"Parallel Search Complete. Total items found: {len(combined_jobs)}")
    return combined_jobs
