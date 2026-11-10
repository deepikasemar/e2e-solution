"""Job ranking: skill overlap, semantic similarity and preferences.

Match = w1 * skill score + w2 * semantic similarity + w3 * preference score

Name, email, phone, gender and age are not inputs to the score.
"""

from __future__ import annotations

import re

from applyagent.cleaner import clean_text
from applyagent.config import DEFAULT_WEIGHTS
from applyagent.embeddings import semantic_scores
from applyagent.skills import extract_skills

PUNJAB_TOKENS = (
    "punjab",
    "chandigarh",
    "mohali",
    "amritsar",
    "ludhiana",
    "jalandhar",
    "gurdaspur",
    "patiala",
    "bathinda",
    "hoshiarpur",
)

_ROLE_STOP = {"and", "or", "the", "for", "with", "role", "developer", "engineer", "junior", "senior", "entry", "level"}


def prepare_job(raw: dict) -> dict:
    description = clean_text(raw.get("description") or "")
    skills = extract_skills(f"{raw.get('title') or ''}\n{description}")
    return {
        "id": str(raw["id"]),
        "title": (raw.get("title") or "").strip(),
        "company": (raw.get("company") or "").strip(),
        "location": (raw.get("location") or "").strip(),
        "work_type": (raw.get("work_type") or "onsite").strip().lower(),
        "description": description,
        "skills": skills,
        "posted_date": (raw.get("posted_date") or "")[:10],
        "url": (raw.get("url") or "").strip(),
        "source": (raw.get("source") or "sample").strip(),
        "salary": (raw.get("salary") or "").strip(),
        "level": (raw.get("level") or "any").strip().lower(),
    }


def profile_match_text(profile: dict) -> str:
    """Text used for embeddings. Identity fields are left out."""
    education = " ".join(
        f"{item.get('degree', '')} {item.get('institution', '')} {item.get('details', '')}"
        for item in profile.get("education") or []
    )
    experience_bits = []
    for item in profile.get("experience") or []:
        bullets = item.get("bullets") or ""
        experience_bits.append(f"{item.get('title', '')} {bullets}")
    projects = " ".join(
        f"{item.get('name', '')} {item.get('description', '')}" for item in profile.get("projects") or []
    )
    skills = " ".join(profile.get("skills") or [])
    parts = [profile.get("headline") or "", profile.get("summary") or "", skills, education, " ".join(experience_bits), projects]
    return "\n".join(part for part in parts if part).strip()


def job_match_text(job: dict) -> str:
    skills = " ".join(job.get("skills") or [])
    return "\n".join(
        part
        for part in (job.get("title") or "", job.get("description") or "", skills, job.get("location") or "")
        if part
    )


def weights_of(profile: dict | None) -> dict[str, float]:
    raw = {}
    if profile:
        raw = (profile.get("preferences") or {}).get("weights") or {}
    values = {}
    for key, default in DEFAULT_WEIGHTS.items():
        try:
            values[key] = float(raw.get(key, default))
        except (TypeError, ValueError):
            values[key] = default
        if values[key] < 0:
            values[key] = 0.0
    total = sum(values.values())
    if total <= 0:
        return dict(DEFAULT_WEIGHTS)
    return {key: value / total for key, value in values.items()}


def skill_score(profile_skills: list[str], job_skills: list[str]) -> tuple[float, list[str], list[str]]:
    """Skill score = |profile ∩ job| / |job|."""
    profile_set = set(profile_skills or [])
    job_set = set(job_skills or [])
    matched = sorted(profile_set & job_set)
    missing = sorted(job_set - profile_set)
    if not job_set:
        return 0.0, matched, missing
    return len(matched) / len(job_set), matched, missing


def preference_score(profile: dict, job: dict) -> float:
    prefs = profile.get("preferences") or {}
    parts = [
        _work_type_score(prefs.get("work_type") or "any", job.get("work_type") or ""),
        _location_score(prefs.get("locations") or "", job),
        _role_score(prefs.get("target_role") or "", job.get("title") or ""),
        _level_score(prefs.get("level") or "any", job.get("level") or "any"),
    ]
    return sum(parts) / len(parts)


def _work_type_score(wanted: str, actual: str) -> float:
    wanted = wanted.lower()
    actual = actual.lower()
    if wanted in {"", "any"}:
        return 1.0
    if wanted == actual:
        return 1.0
    if wanted == "hybrid" and actual in {"remote", "onsite", "hybrid"}:
        return 0.55
    return 0.2


def _location_score(locations: str, job: dict) -> float:
    tokens = [part.strip().lower() for part in re.split(r"[,/]|\bor\b", locations) if part.strip()]
    if not tokens:
        return 1.0
    haystack = f"{job.get('location') or ''} {job.get('work_type') or ''}".lower()
    for token in tokens:
        if token in haystack:
            return 1.0
        if token == "punjab" and any(city in haystack for city in PUNJAB_TOKENS):
            return 1.0
        if token == "remote" and "remote" in haystack:
            return 1.0
    return 0.15


def _role_score(role: str, title: str) -> float:
    words = [word for word in re.findall(r"[a-z]+", role.lower()) if len(word) > 2 and word not in _ROLE_STOP]
    if not words:
        return 1.0
    title_l = title.lower()
    hits = sum(1 for word in words if word in title_l)
    return 0.25 + 0.75 * (hits / len(words))


def _level_score(wanted: str, actual: str) -> float:
    wanted = wanted.lower()
    actual = actual.lower()
    if wanted in {"", "any"} or actual in {"", "any"} or wanted == actual:
        return 1.0
    if {wanted, actual} == {"entry", "intern"}:
        return 0.75
    return 0.3


def rank_jobs(profile: dict, jobs: list[dict]) -> tuple[list[dict], str]:
    prepared = [job if job.get("skills") is not None and "description" in job else prepare_job(job) for job in jobs]
    weights = weights_of(profile)
    profile_skills = list(profile.get("skills") or [])
    semantics, backend = semantic_scores(profile_match_text(profile), [job_match_text(job) for job in prepared])
    ranked: list[dict] = []
    for job, semantic in zip(prepared, semantics):
        skill, matched, missing = skill_score(profile_skills, job.get("skills") or [])
        preference = preference_score(profile, job)
        total = (
            weights["skill"] * skill
            + weights["semantic"] * semantic
            + weights["preference"] * preference
        )
        ranked.append(
            {
                **job,
                "skill_score": skill,
                "semantic_score": semantic,
                "preference_score": preference,
                "score": total,
                "matched_skills": matched,
                "missing_skills": missing,
                "weights": weights,
            }
        )
    ranked.sort(key=lambda item: (-item["score"], item.get("title") or ""))
    return ranked, backend
