"""
Scraper registry.

Phase 4.1 keeps the original scrape functions unchanged and simply maps a
stable source name to each. Phase 4.4 reshapes them to the ``Scraper`` protocol
in :mod:`recruit_engine.scrapers.base` (per-call rate limiting, ``ProfileSpec``
in, ``list[JobPosting]`` out) and threads the ``big3_optin`` gate through jobspy.

Dropped for the SaaS: Naukri, Unstop, Internshala, Cutshort (undocumented
endpoints / HTML scraping). ``serpapi_scraper`` stays in-tree but is
intentionally unregistered — it is opt-in and needs a user-supplied key.
"""

from .hn_scraper import scrape_hn_hiring
from .jobspy_scraper import scrape_jobspy
from .wellfound_scraper import scrape_wellfound
from .yc_scraper import scrape_yc_jobs

SCRAPERS = {
    "jobspy": scrape_jobspy,
    "wellfound": scrape_wellfound,
    "yc": scrape_yc_jobs,
    "hackernews": scrape_hn_hiring,
}

__all__ = ["SCRAPERS", "scrape_jobspy", "scrape_wellfound", "scrape_yc_jobs", "scrape_hn_hiring"]
