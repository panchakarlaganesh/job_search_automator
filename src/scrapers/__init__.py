# scrapers package — re-exports from both the parent scrapers.py module
# and the linkedin_guest submodule so both import styles work:
#   from src.scrapers import fetch_all_jobs          (main.py)
#   from src.scrapers.linkedin_guest import ...      (guest scraper)
import importlib, sys, os

# Dynamically load src/scrapers.py as src._scrapers_flat to avoid name clash
_parent = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scrapers.py")
_spec = importlib.util.spec_from_file_location("src._scrapers_flat", _parent)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

fetch_all_jobs   = _mod.fetch_all_jobs
fetch_naukri_jobs = _mod.fetch_naukri_jobs

from .linkedin_guest import fetch_linkedin_guest_jobs

__all__ = ["fetch_all_jobs", "fetch_naukri_jobs", "fetch_linkedin_guest_jobs"]

