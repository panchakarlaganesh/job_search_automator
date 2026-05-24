import asyncio
from playwright.async_api import async_playwright
from .logger import logger
from .memory import get_remembered_answer, remember_answer
from .evaluator import answer_application_question
from .models import JobStatus

class BaseApplier:
    def __init__(self, headless=True):
        self.headless = headless

    async def apply(self, job, resume_path, base_resume_content):
        raise NotImplementedError

class GreenhouseApplier(BaseApplier):
    async def apply(self, job, resume_path, base_resume_content):
        logger.info(f"Attempting Greenhouse application for {job.title} at {job.company}")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                await page.goto(job.url)
                # Fill basic fields
                await page.fill("#first_name", "Firstname") # User should config these
                await page.fill("#last_name", "Lastname")
                await page.fill("#email", "email@example.com")
                await page.fill("#phone", "1234567890")
                
                # Upload resume
                async with page.expect_file_chooser() as fc_info:
                    await page.click("[data-source='attach']")
                file_chooser = await fc_info.value
                await file_chooser.set_files(resume_path)
                
                # Handle custom questions
                questions = await page.query_selector_all(".custom-question")
                for q in questions:
                    label = await q.query_selector("label")
                    if label:
                        q_text = await label.inner_text()
                        answer = get_remembered_answer(q_text)
                        if not answer:
                            answer = answer_application_question(q_text, job.description, base_resume_content)
                            remember_answer(q_text, answer)
                        
                        input_field = await q.query_selector("input, textarea, select")
                        if input_field:
                            await input_field.fill(answer)
                
                # Submit (commented out for safety during dev)
                # await page.click("#submit_app")
                logger.info(f"Successfully filled application for {job.title}")
                return True
            except Exception as e:
                logger.error(f"Greenhouse application error: {e}")
                return False
            finally:
                await browser.close()

class LeverApplier(BaseApplier):
    async def apply(self, job, resume_path, base_resume_content):
        logger.info(f"Attempting Lever application for {job.title} at {job.company}")
        # Implementation similar to Greenhouse with Lever-specific selectors
        return False # Placeholder

def get_applier(url):
    if "greenhouse.io" in url:
        return GreenhouseApplier()
    elif "lever.co" in url:
        return LeverApplier()
    return None
