import asyncio
from playwright.async_api import async_playwright

async def check():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            url = 'https://www.dice.com/jobs?q=Site%20Reliability%20Engineer&location=United%20States&pageSize=20&postedDate=3'
            print(f"Navigating to: {url}")
            await page.goto(url, wait_until="load", timeout=60000)
            await asyncio.sleep(10)
            
            content = await page.content()
            print(f"Content Length: {len(content)}")
            
            # Look for common dice markers
            markers = ["d-job-card", "search-card", "card-title", "company-name", "job-result-card"]
            for m in markers:
                print(f"Marker '{m}' found: {m in content}")
            
            # Take screenshot
            import os
            os.makedirs("logs", exist_ok=True)
            await page.screenshot(path="logs/dice_debug_raw.png")
            print("Screenshot saved to logs/dice_debug_raw.png")
            
            # List some classes of div elements
            classes = await page.evaluate("""() => {
                const divs = Array.from(document.querySelectorAll('div[class]')).slice(0, 50);
                return divs.map(d => d.className);
            }""")
            print("Sample Classes:", list(set(classes))[:10])

        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(check())
