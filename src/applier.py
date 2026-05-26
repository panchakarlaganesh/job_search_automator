from src.logger import logger

class BaseApplier:
    async def apply(self, job, resume_path, base_resume):
        raise NotImplementedError

def get_applier(url):
    """
    Returns an applier instance based on the job URL.
    For now, we return None as we focus on manual review.
    """
    # Logic to return specialized appliers (e.g., LinkedInApplier) would go here
    return None
