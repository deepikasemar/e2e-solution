"""Collect postings from the bundled set and from permitted public sources.

Live sources are optional. A failure there does not remove jobs already
stored, and the sample set always remains available offline.
"""

from __future__ import annotations

import json
import urllib.request
from datetime import datetime

from applyagent.cleaner import clean_text, dedup_key
from applyagent.seed import JOBS

REMOTIVE_URL = "https://remotive.com/api/remote-jobs?category=software-dev"
WWR_URL = "https://weworkremotely.com/categories/remote-programming-jobs.rss"


def sample_jobs() -> list[dict]:
    return [dict(job) for job in JOBS]


def collect_live(limit: int = 30) -> tuple[list[dict], list[dict]]:
    """Return (jobs, source reports). Reports include errors in plain language."""
    jobs: list[dict] = []
    reports: list[dict] = []
    for name, fetcher in (("remotive", _remotive), ("weworkremotely", _weworkremotely)):
        try:
            found = fetcher(limit)
            jobs.extend(found)
            reports.append({"source": name, "ok": True, "count": len(found), "error": ""})
        except Exception as exc:
            reports.append({"source": name, "ok": False, "count": 0, "error": exc.__class__.__name__})
    return _dedupe(jobs), reports


def _dedupe(jobs: list[dict]) -> list[dict]:
    seen: set[str] = set()
    kept: list[dict] = []
    for job in jobs:
        key = dedup_key(job.get("title") or "", job.get("company") or "")
        if not key or key in seen:
            continue
        seen.add(key)
        kept.append(job)
    return kept


def _remotive(limit: int) -> list[dict]:
    request = urllib.request.Request(REMOTIVE_URL, headers={"User-Agent": "ApplyAgent/1.0 (educational prototype)"})
    with urllib.request.urlopen(request, timeout=12) as response:
        payload = json.loads(response.read().decode())
    jobs = []
    for item in payload.get("jobs", [])[:limit]:
        title = (item.get("title") or "").strip()
        company = (item.get("company_name") or "").strip()
        if not title or not company:
            continue
        description = clean_text(item.get("description") or "")
        posted = (item.get("publication_date") or "")[:10]
        jobs.append(
            {
                "id": f"remotive-{item.get('id')}",
                "title": title,
                "company": company,
                "location": (item.get("candidate_required_location") or "Remote").strip(),
                "work_type": "remote",
                "level": _guess_level(title),
                "salary": (item.get("salary") or "").strip(),
                "posted_date": posted,
                "url": (item.get("url") or "").strip(),
                "source": "remotive",
                "description": description,
            }
        )
    return jobs


def _weworkremotely(limit: int) -> list[dict]:
    import feedparser

    feed = feedparser.parse(WWR_URL)
    if getattr(feed, "bozo", False) and not feed.entries:
        raise RuntimeError("RSS feed could not be read")
    jobs = []
    for entry in feed.entries[:limit]:
        title = (entry.get("title") or "").strip()
        company = ""
        if ":" in title:
            company, title = [part.strip() for part in title.split(":", 1)]
        description = clean_text(entry.get("summary") or entry.get("description") or "")
        posted = ""
        if entry.get("published_parsed"):
            posted = datetime(*entry.published_parsed[:6]).date().isoformat()
        link = (entry.get("link") or "").strip()
        jobs.append(
            {
                "id": "wwr-" + str(abs(hash(link or title)) % 10**12),
                "title": title or "Programming role",
                "company": company or "We Work Remotely",
                "location": "Remote",
                "work_type": "remote",
                "level": _guess_level(title),
                "salary": "",
                "posted_date": posted,
                "url": link,
                "source": "weworkremotely",
                "description": description,
            }
        )
    return jobs


def _guess_level(title: str) -> str:
    lowered = title.lower()
    if "intern" in lowered:
        return "intern"
    if "senior" in lowered or "staff" in lowered or "lead" in lowered:
        return "mid"
    if "junior" in lowered or "graduate" in lowered or "entry" in lowered:
        return "entry"
    return "any"
