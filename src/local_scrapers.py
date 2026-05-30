import asyncio
import random
import os
from playwright.async_api import async_playwright
from src.logger import logger
from datetime import datetime

# --- Browser Utilities ---

async def get_stealth_context(p):
    browser = await p.chromium.launch(headless=True, args=[
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox",
        "--disable-setuid-sandbox"
    ])
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    ]
    context = await browser.new_context(
        user_agent=random.choice(user_agents),
        viewport={'width': random.randint(1280, 1920), 'height': random.randint(720, 1080)},
        extra_http_headers={"Accept-Language": "en-US,en;q=0.9"}
    )
    return browser, context

async def human_scroll(page):
    for _ in range(random.randint(2, 4)):
        await page.mouse.wheel(0, random.randint(400, 800))
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
        browser, context = await get_stealth_context(p)
        page = await context.new_page()
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
                            
                            # Deep Scrape Description
                            full_desc = await fetch_full_description(page, job_url, "#jobDescriptionText, .jobsearch-JobComponent-description")
                            
                            jobs.append({
                                "job_id_external": f"ind_{href.split('jk=')[-1][:16]}" if "jk=" in href else f"ind_{random.randint(1,999999)}",
                                "title": title, "company": company, "location": loc, "url": job_url,
                                "source": "indeed", "description": full_desc or f"Indeed: {title} @ {company}", "posted_date": datetime.now()
                            })
                except Exception as e: logger.error(f"Indeed Error: {e}")
        await browser.close()
    return jobs

async def scrape_dice(keywords, locations, max_items, days_back):
    jobs = []
    async with async_playwright() as p:
        browser, context = await get_stealth_context(p)
        page = await context.new_page()
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
                            
                            # Deep Scrape Description
                            full_desc = await fetch_full_description(page, job_url, "#jobDescription, .job-details")

                            jobs.append({
                                "job_id_external": f"dice_{href.split('/')[-1][:12]}",
                                "title": title, "company": company, "location": loc, "url": job_url,
                                "source": "dice", "description": full_desc or f"Dice: {title} @ {company}", "posted_date": datetime.now()
                            })
                except Exception as e: logger.error(f"Dice Error: {e}")
        await browser.close()
    return jobs

async def scrape_linkedin(keywords, locations, max_items, days_back):
    jobs = []
    async with async_playwright() as p:
        browser, context = await get_stealth_context(p)
        page = await context.new_page()
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
                        company_el = await card.query_selector(".base-search-card__subtitle, h4")
                        link_el = await card.query_selector("a.base-card__full-link, a")
                        if title_el and link_el:
                            title = (await title_el.inner_text()).strip()
                            company = (await company_el.inner_text()).strip() if company_el else "Unknown"
                            job_url = (await link_el.get_attribute("href")).split('?')[0]
                            
                            # Deep Scrape Description
                            full_desc = await fetch_full_description(page, job_url, ".show-more-less-html__markup, .description__text")

                            jobs.append({
                                "job_id_external": f"li_{random.randint(1000000, 9999999)}",
                                "title": title, "company": company, "location": loc, "url": job_url,
                                "source": "linkedin", "description": full_desc or f"LinkedIn: {title} @ {company}", "posted_date": datetime.now()
                            })
                except Exception as e: logger.error(f"LinkedIn Error: {e}")
        await browser.close()
    return jobs

async def scrape_ziprecruiter(keywords, locations, max_items, days_back):
    jobs = []
    async with async_playwright() as p:
        browser, context = await get_stealth_context(p)
        page = await context.new_page()
        for kw in keywords:
            for loc in locations:
                url = f"https://www.ziprecruiter.com/jobs-search?search={kw.replace(' ', '+')}&location={loc.replace(' ', '+')}&days={days_back}"
                try:
                    logger.info(f"ZipRecruiter: Searching {kw} in {loc}...")
                    await page.goto(url, wait_until="load")
                    cards = await page.query_selector_all(".job_content")
                    for card in cards[:max_items]:
                        title_el = await card.query_selector(".job_title")
                        company_el = await card.query_selector(".company_name")
                        link_el = await card.query_selector("a.job_link")
                        if title_el and link_el:
                            title = (await title_el.inner_text()).strip()
                            company = (await company_el.inner_text()).strip() if company_el else "Unknown"
                            job_url = await link_el.get_attribute("href")
                            
                            # Deep Scrape Description
                            full_desc = await fetch_full_description(page, job_url, ".job_description")

                            jobs.append({
                                "job_id_external": f"zr_{random.randint(100000, 999999)}",
                                "title": title, "company": company, "location": loc, "url": job_url,
                                "source": "ziprecruiter", "description": full_desc or f"ZipRecruiter: {title} @ {company}", "posted_date": datetime.now()
                            })
                except Exception as e: logger.error(f"ZipRecruiter Error: {e}")
        await browser.close()
    return jobs

async def scrape_glassdoor(keywords, locations, max_items, days_back):
    jobs = []
    async with async_playwright() as p:
        browser, context = await get_stealth_context(p)
        page = await context.new_page()
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
                        company_el = await card.query_selector("[data-test='employer-short-name']")
                        if title_el:
                            title = (await title_el.inner_text()).strip()
                            company = (await company_el.inner_text()).strip() if company_el else "Unknown"
                            href = await title_el.get_attribute("href")
                            job_url = f"https://www.glassdoor.com{href}" if href and not href.startswith("http") else href
                            
                            # Deep Scrape Description
                            full_desc = await fetch_full_description(page, job_url, "[data-test='jobDescriptionText']")

                            jobs.append({
                                "job_id_external": f"gd_{random.randint(100000, 999999)}",
                                "title": title, "company": company, "location": loc, "url": job_url,
                                "source": "glassdoor", "description": full_desc or f"Glassdoor: {title} @ {company}", "posted_date": datetime.now()
                            })
                except Exception as e: logger.error(f"Glassdoor Error: {e}")
        await browser.close()
    return jobs

# --- Main Entry Point (Parallel) ---

async def fetch_local_jobs_async(keywords, locations, days_back=3):
    """Runs all scrapers in parallel and combines results."""
    logger.info("Starting Parallel Multi-Board Search with Deep Scraping...")
    
    # Define tasks for all sources
    # We limit items per board to 10 for deep scraping efficiency
    tasks = [
        scrape_indeed(keywords, locations, 10, days_back),
        scrape_dice(keywords, locations, 10, days_back),
        scrape_linkedin(keywords, locations, 10, days_back),
        scrape_ziprecruiter(keywords, locations, 10, days_back),
        scrape_glassdoor(keywords, locations, 10, days_back)
    ]
    
    # Execute in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    combined_jobs = []
    for res in results:
        if isinstance(res, list):
            combined_jobs.extend(res)
        elif isinstance(res, Exception):
            logger.error(f"One of the parallel scrapers failed: {res}")
            
    logger.info(f"Parallel Search Complete. Total unique items found: {len(combined_jobs)}")
    return combined_jobs
