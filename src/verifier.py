import asyncio
from playwright.async_api import async_playwright
from src.logger import logger

async def verify_job_active(url):
    """
    Checks if a job application link is still active.
    Specifically looks for Greenhouse/Lever 'Job not found' messages.
    """
    if not url: return True
    
    # We only verify certain ATS types to save time
    is_ats = any(x in url.lower() for x in ["greenhouse.io", "lever.co", "ashbyhq.com", "workday.com"])
    if not is_ats: return True

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(url, wait_until="load", timeout=30000)
            content = await page.content()
            
            # Common "Expired" markers
            expired_markers = [
                "job no longer available",
                "link has expired",
                "job not found",
                "this position is closed",
                "no longer accepting applications"
            ]
            
            for marker in expired_markers:
                if marker in content.lower():
                    logger.info(f"Ghost Job Detected: {url}")
                    return False
            
            return True
        except Exception as e:
            logger.debug(f"Verification failed for {url}: {e}")
            return True # Assume active if we can't tell
        finally:
            await browser.close()

def get_ats_type(url):
    url = url.lower()
    if "greenhouse.io" in url: return "greenhouse"
    if "lever.co" in url: return "lever"
    if "ashbyhq.com" in url: return "ashby"
    if "myworkdayjobs.com" in url: return "workday"
    return "other"
