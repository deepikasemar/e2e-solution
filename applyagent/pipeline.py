"""Connect profile, ranking, drafting and the tracker."""

from __future__ import annotations

import time

from applyagent.db import (
    APPLIED_STATES,
    count_applied_on,
    create_application,
    find_open_draft,
    get_job,
    get_profile,
    today_key,
    update_application,
)
from applyagent.config import daily_limit
from applyagent.factcheck import check_documents
from applyagent.generator import generate_documents
from applyagent.matcher import rank_jobs


class PipelineError(Exception):
    pass


def draft_application(job_id: str) -> int:
    profile = get_profile()
    if not profile or not (profile.get("full_name") or profile.get("skills")):
        raise PipelineError("Save a verified profile before drafting an application.")
    if not profile.get("skills"):
        raise PipelineError("Add at least one skill to the profile. The agent will not guess skills for you.")
    job = get_job(job_id)
    if not job:
        raise PipelineError("That job is no longer in the local database.")
    existing = find_open_draft(job_id)
    if existing:
        return int(existing["id"])
    ranked, backend = rank_jobs(profile, [job])
    match = ranked[0]
    match["backend"] = backend
    started = time.perf_counter()
    summary, letter, writer = generate_documents(profile, job, match["matched_skills"])
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    flags = check_documents(profile, summary, letter)
    packet = application_packet(profile, job, summary, letter)
    return create_application(
        {
            "job_id": job["id"],
            "company": job["company"],
            "title": job["title"],
            "status": "draft",
            "summary": summary,
            "cover_letter": letter,
            "writer": writer,
            "fact_flags": flags,
            "match": _public_match(match),
            "form": packet,
            "generation_ms": elapsed_ms,
        }
    )


def refresh_draft(application: dict, summary: str, letter: str) -> dict:
    profile = get_profile() or {}
    flags = check_documents(profile, summary, letter)
    job = get_job(application["job_id"]) if application.get("job_id") else None
    packet = application_packet(profile, job or application, summary, letter)
    update_application(
        application["id"],
        summary=summary,
        cover_letter=letter,
        fact_flags=flags,
        form_json=packet,
    )
    application["summary"] = summary
    application["cover_letter"] = letter
    application["fact_flags"] = flags
    application["form"] = packet
    return application


def mark_applied(application: dict) -> None:
    if application["status"] not in {"approved", *APPLIED_STATES}:
        raise PipelineError("Approve the draft before recording it as applied.")
    if application.get("applied_on"):
        update_application(application["id"], status="applied")
        return
    if count_applied_on() >= daily_limit():
        raise PipelineError(
            f"Today's limit is {daily_limit()} recorded applications (India time). "
            "It resets at midnight IST. Nothing was sent to an employer."
        )
    update_application(application["id"], status="applied", applied_on=today_key())


def application_packet(profile: dict, job: dict, summary: str, letter: str) -> dict:
    return {
        "full_name": profile.get("full_name") or "",
        "email": profile.get("email") or "",
        "phone": profile.get("phone") or "",
        "location": profile.get("location") or "",
        "target_role": (profile.get("preferences") or {}).get("target_role") or "",
        "company": job.get("company") or "",
        "job_title": job.get("title") or "",
        "job_url": job.get("url") or "",
        "skills": list(profile.get("skills") or []),
        "summary": summary,
        "cover_letter": letter,
    }


def _public_match(match: dict) -> dict:
    keys = (
        "score",
        "skill_score",
        "semantic_score",
        "preference_score",
        "matched_skills",
        "missing_skills",
        "weights",
        "backend",
        "skills",
    )
    return {key: match.get(key) for key in keys}
