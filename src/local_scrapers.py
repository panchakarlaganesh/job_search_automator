import asyncio
import random
import os
from playwright.async_api import async_playwright
from src.logger import logger
from datetime import datetime

async def scrape_indeed_playwright(keywords, locations, max_items=10, days_back=3):
    jobs = []
    async with async_playwright() as p:
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
                url = f"https://{domain}/jobs?q={kw.replace(' ', '+')}&l={loc.replace(' ', '+')}&fromage={days_back}"
                try:
                    logger.info(f"Navigating to Indeed {loc}...")
                    await page.goto(url, wait_until="load", timeout=60000)
                    
                    for _ in range(3):
                        await page.mouse.wheel(0, 500)
                        await asyncio.sleep(random.uniform(1, 3))

                    try:
                        await page.click("button.icl-CloseButton", timeout=3000)
                    except: pass

                    job_cards = await page.query_selector_all(".job_seen_beacon, .result, div.cardOutline")
                    logger.info(f"Found {len(job_cards)} job cards on Indeed ({loc}).")
                    
                    if not job_cards:
                        os.makedirs("logs", exist_ok=True)
                        await page.screenshot(path=f"logs/blocked_{loc}.png")
                        if "Blocked" in await page.title():
                            logger.error(f"Indeed blocked the request for {loc}.")
                            continue

                    seen_urls = set()
                    for card in job_cards[:max_items * 2]:
                        if len(jobs) >= max_items: break
                        
                        title_elem = await card.query_selector("h2.jobTitle span, a.jcs-JobTitle, .jobTitle")
                        title = (await title_elem.inner_text()).strip() if title_elem else "Unknown Title"
                        
                        company_elem = await card.query_selector("[data-testid='company-name'], .companyName, .provider")
                        company = (await company_elem.inner_text()).strip() if company_elem else "Unknown Company"
                        
                        link_elem = await card.query_selector("h2.jobTitle a, a.jcs-JobTitle")
                        job_url_rel = await link_elem.get_attribute("href") if link_elem else ""
                        job_url = f"https://{domain}{job_url_rel}" if job_url_rel and not job_url_rel.startswith("http") else job_url_rel
                        
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

async def scrape_dice_playwright(keywords, locations, max_items=10, days_back=3):
    jobs = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
        page = await context.new_page()
        
        for kw in keywords:
            for loc in locations:
                url = f"https://www.dice.com/jobs?q={kw.replace(' ', '%20')}&location={loc.replace(' ', '%20')}&pageSize=20&language=en&postedDate={days_back}"
                try:
                    logger.info(f"Navigating to Dice {loc}...")
                    await page.goto(url, wait_until="load", timeout=60000)
                    await asyncio.sleep(5)
                    
                    job_cards = await page.query_selector_all("d-job-card, .card, [id^='google-ad-content'], .search-card")
                    logger.info(f"Found {len(job_cards)} job cards on Dice ({loc}).")
                    
                    if not job_cards:
                        # Debug: Screenshot of Dice failure
                        os.makedirs("logs", exist_ok=True)
                        await page.screenshot(path=f"logs/dice_failed_{loc}.png")

                    seen_urls = set()
                    for card in job_cards:
                        if len(jobs) >= max_items: break
                        
                        # Primary selector for Dice titles
                        title_elem = await card.query_selector("a.card-title-link, .title, h5, a[id^='job-title']")
                        title = (await title_elem.inner_text()).strip() if title_elem else "Unknown Title"
                        
                        link_elem = await card.query_selector("a.card-title-link, a")
                        job_url = await link_elem.get_attribute("href") if link_elem else ""
                        
                        if not job_url or job_url in seen_urls: continue
                        seen_urls.add(job_url)

                        company_elem = await card.query_selector("[data-cy='card-company-name'], .company")
                        company = (await company_elem.inner_text()).strip() if company_elem else "Unknown Company"
                        
                        jobs.append({
                            "job_id_external": f"dice_{random.randint(100000, 999999)}",
                            "title": title,
                            "company": company,
                            "location": loc,
                            "url": job_url,
                            "source": "dice",
                            "description": f"Role at {company}",
                            "posted_date": datetime.now()
                        })
                except Exception as e:
                    logger.error(f"Dice scraper failed for {loc}: {e}")
                    
        await browser.close()
    return jobs

async def scrape_linkedin_playwright(keywords, locations, max_items=10, days_back=3):
    jobs = []
    async with async_playwright() as p:
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
        page = await context.new_page()

        for kw in keywords:
            for loc in locations:
                time_map = {1: "r86400", 2: "r172800", 3: "r259200", 7: "r604800"}
                f_tpr = time_map.get(days_back, "r604800")
                
                search_url = f"https://www.linkedin.com/jobs/search/?keywords={kw.replace(' ', '%20')}&location={loc.replace(' ', '%20')}&f_TPR={f_tpr}"
                
                try:
                    logger.info(f"Navigating to LinkedIn {loc} (last {days_back} days)...")
                    await page.goto(search_url, wait_until="load", timeout=60000)
                    await asyncio.sleep(random.uniform(3, 5))
                    
                    job_cards = await page.query_selector_all(".base-card, .job-search-card, li")
                    logger.info(f"Found {len(job_cards)} potential items on LinkedIn ({loc}).")

                    seen_urls = set()
                    for card in job_cards:
                        if len(jobs) >= max_items: break
                        try:
                            title_elem = await card.query_selector(".base-search-card__title, .job-search-card__title, h3")
                            if not title_elem: continue
                            title = (await title_elem.inner_text()).strip()
                            
                            company_elem = await card.query_selector(".base-search-card__subtitle, .job-search-card__subtitle, h4")
                            company = (await company_elem.inner_text()).strip() if company_elem else "Unknown Company"
                            
                            link_elem = await card.query_selector("a.base-card__full-link, a.job-search-card__link")
                            if not link_elem: continue
                            job_url = await link_elem.get_attribute("href")
                            if job_url: job_url = job_url.split('?')[0]

                            if not job_url or job_url in seen_urls: continue
                            seen_urls.add(job_url)

                            jobs.append({
                                "job_id_external": f"li_{random.randint(1000000, 9999999)}",
                                "title": title,
                                "company": company,
                                "location": loc,
                                "url": job_url,
                                "source": "linkedin",
                                "description": f"LinkedIn position: {title} at {company}",
                                "posted_date": datetime.now()
                            })
                        except: continue
                except Exception as e:
                    logger.error(f"LinkedIn scraper failed for {loc}: {e}")
                    os.makedirs("logs", exist_ok=True)
                    await page.screenshot(path=f"logs/li_blocked_{loc}.png")
        await browser.close()
    return jobs

async def fetch_local_jobs_async(keywords, locations, days_back=3):
    indeed_jobs = await scrape_indeed_playwright(keywords, locations, 10, days_back)
    dice_jobs = await scrape_dice_playwright(keywords, locations, 10, days_back)
    linkedin_jobs = await scrape_linkedin_playwright(keywords, locations, 10, days_back)
    return indeed_jobs + dice_jobs + linkedin_jobs
