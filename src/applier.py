import sys
import os
import re
import pathlib
import asyncio
import json
from datetime import datetime, timezone
from src.logger import logger

# Force UTF-8 output so emoji in browser-use logs don't crash on Windows cp1252
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

class BaseApplier:
    async def apply(self, job, resume_path, base_resume):
        raise NotImplementedError

    def _archive_posting(self, job) -> pathlib.Path | None:
        """Save verbatim job posting to disk before the browser agent holds it.

        Ported from upstream fix 0e1a895: /apply archives the job posting while
        it still holds it in context, preventing loss when the listing expires.
        File: documents/applications/<company>_<role>/job_posting.md
        """
        safe = re.compile(r"[^\w\-]")  # keep word chars and hyphens
        company_slug = safe.sub("_", (job.company or "unknown").strip()).lower()
        role_slug = safe.sub("_", (job.title or "role").strip()).lower()
        folder = pathlib.Path("documents") / "applications" / f"{company_slug}_{role_slug}"
        folder.mkdir(parents=True, exist_ok=True)
        posting_path = folder / "job_posting.md"
        try:
            content_lines = [
                f"# {job.title} — {job.company}",
                f"",
                f"**URL:** {job.url}",
                f"**Archived:** {datetime.now(timezone.utc).isoformat()}",
                f"**Source:** {getattr(job, 'source', 'unknown')}",
                f"",
                "---",
                f"",
                getattr(job, "description", "") or "_(no description available)_",
            ]
            posting_path.write_text("\n".join(content_lines), encoding="utf-8")
            logger.info(f"Archived job posting to {posting_path}")
            return posting_path
        except OSError as e:
            logger.warning(f"Could not archive job posting: {e}")
            return None

class BrowserUseApplier(BaseApplier):
    async def apply(self, job, resume_path, base_resume):
        logger.info(f"Starting browser-use auto-apply agent for {job.company} - {job.title}...")

        # Archive the posting immediately before the browser agent runs (upstream fix 0e1a895).
        # This preserves the full job text even if the listing expires mid-session.
        self._archive_posting(job)
        
        try:
            from browser_use.agent.service import Agent
            from browser_use.browser.session import BrowserSession
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
        
        # Build Gemini LLM for browser-use v0.13.1
        from google import genai as google_genai
        from browser_use.llm.google.chat import ChatGoogle
        llm = ChatGoogle(model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))

        # Read credentials from env
        naukri_email    = os.getenv("NAUKRI_EMAIL", "")
        naukri_password = os.getenv("NAUKRI_PASSWORD", "")
        linkedin_email    = os.getenv("LINKEDIN_EMAIL", "")
        linkedin_password = os.getenv("LINKEDIN_PASSWORD", "")

        task_text = (
            f"Your goal: apply for the job at this URL: {job.url}\n\n"
            f"== LOGIN INSTRUCTIONS ==\n"
            f"If you land on a Naukri.com login page:\n"
            f"  - Email: {naukri_email}\n"
            f"  - Password: {naukri_password}\n"
            f"If you land on a LinkedIn login page:\n"
            f"  - Email: {linkedin_email}\n"
            f"  - Password: {linkedin_password}\n"
            f"After logging in, navigate back to the job URL and apply.\n\n"
            f"== APPLICATION INSTRUCTIONS ==\n"
            f"- Fill out the application form for '{job.title}' at '{job.company}'.\n"
            f"- Use the candidate resume below for all fields (name, email, phone, experience, skills).\n"
            f"- If there is a file upload field for Resume/CV, upload: {os.path.abspath(resume_path)}\n"
            f"- If the job listing is expired or removed, stop immediately and report it.\n"
            f"- Once all fields are filled, verify and submit the application.\n\n"
            f"== CANDIDATE RESUME ==\n"
            f"{base_resume}"
        )

        logger.info(f"Launching autonomous agent with URL: {job.url}")

        # headed=True so the user can see the browser and handle logins manually
        browser_session = BrowserSession(headless=False)

        agent = Agent(
            task=task_text,
            llm=llm,
            browser_session=browser_session,
        )
        
        try:
            result = await agent.run(max_steps=30)
            result_text = ""
            try:
                result_text = str(result)
            except Exception:
                result_text = repr(result)

            # Detect expired listing from agent result
            if "EXPIRED" in result_text.upper() or "expired" in result_text.lower():
                logger.warning(f"Job listing expired: {job.company} - {job.title}")
                return "EXPIRED"

            logger.info(f"Agent finished applying to {job.company}.")
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
