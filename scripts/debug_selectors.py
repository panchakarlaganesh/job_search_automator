import asyncio
from playwright.async_api import async_playwright

async def check():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            print("Navigating to Indeed...")
            await page.goto('https://www.indeed.com/jobs?q=SRE&l=Remote', wait_until="networkidle", timeout=60000)
            await asyncio.sleep(5)
            
            # Check for Cloudflare or CAPTCHA
            title = await page.title()
            print(f"Page Title: {title}")
            
            # Get a sample of the body classes/structure
            body_html = await page.evaluate("() => document.body.innerHTML.substring(0, 5000)")
            print("Body Preview (first 5000 chars):")
            print(body_html)
            
            # Specifically look for job-like structures
            divs = await page.query_selector_all("div")
            print(f"Total divs found: {len(divs)}")
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(check())
