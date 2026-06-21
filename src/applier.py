import os
from src.logger import logger

class BaseApplier:
    async def apply(self, job, resume_path, base_resume):
        raise NotImplementedError

class BrowserUseApplier(BaseApplier):
    async def apply(self, job, resume_path, base_resume):
        logger.info(f"Starting browser-use auto-apply agent for {job.company} - {job.title}...")
        
        try:
            from browser_use import Agent
            from browser_use.llm.models import get_llm_by_name
        except ImportError as e:
            logger.error(f"Failed to import browser-use: {e}")
            raise RuntimeError("Auto-apply dependencies are not installed.")
            
        gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not gemini_key:
            from dotenv import dotenv_values
            env_vals = dotenv_values(".env")
            gemini_key = env_vals.get("GEMINI_API_KEY", "").strip()
            
        if not gemini_key:
            raise RuntimeError("GEMINI_API_KEY is not configured in the environment.")
            
        # Set key in environment for browser-use
        os.environ["GOOGLE_API_KEY"] = gemini_key
        
        # Initialize Gemini model for browser-use agent
        llm = get_llm_by_name("google_gemini-2.5-flash")
        
        # Build prompt instructions for the browser agent
        task_text = (
            f"Please go to the job application page: {job.url}\n"
            f"Fill out and submit the application for the position of '{job.title}' at '{job.company}'.\n"
            f"Use the information from the candidate's resume below to answer any questions (e.g. contact info, work history, skills):\n\n"
            f"{base_resume}\n\n"
            f"When you find a file input field to upload a Resume or CV, upload the resume file located at: {os.path.abspath(resume_path)}.\n"
            f"Verify all fields and submit the application once ready."
        )
        
        logger.info(f"Launching autonomous agent with URL: {job.url}")
        
        agent = Agent(
            task=task_text,
            llm=llm
        )
        
        try:
            result = await agent.run()
            logger.info(f"Agent finished applying to {job.company}. Result: {result}")
            return True
        except Exception as e:
            logger.error(f"Agent failed applying to {job.company}: {e}")
            raise

def get_applier(url):
    """
    Returns an applier instance based on the job URL.
    Returns BrowserUseApplier since it can handle any job board autonomously.
    """
    return BrowserUseApplier()
