"""Convert the profile editor fields to and from the stored profile."""

from __future__ import annotations

import re

from applyagent.config import DEFAULT_WEIGHTS
from applyagent.parser import default_preferences, empty_profile
from applyagent.skills import normalize_skill_list


def skills_to_text(skills: list[str]) -> str:
    return ", ".join(skills)


def skills_from_text(text: str) -> list[str]:
    parts = [part.strip() for part in re.split(r"[\n,]", text or "") if part.strip()]
    return normalize_skill_list(parts)


def education_to_text(items: list[dict]) -> str:
    lines = []
    for item in items:
        lines.append(" | ".join([item.get("degree") or "", item.get("institution") or "", item.get("year") or ""]))
    return "\n".join(lines)


def education_from_text(text: str) -> list[dict]:
    items = []
    for line in (text or "").splitlines():
        if not line.strip():
            continue
        parts = [part.strip() for part in line.split("|")]
        while len(parts) < 3:
            parts.append("")
        if not any(parts[:3]):
            continue
        items.append({"degree": parts[0], "institution": parts[1], "year": parts[2], "details": ""})
    return items


def experience_to_text(items: list[dict]) -> str:
    lines = []
    for item in items:
        lines.append(
            " | ".join(
                [
                    item.get("title") or "",
                    item.get("company") or "",
                    item.get("start") or "",
                    item.get("end") or "",
                    item.get("bullets") or "",
                ]
            )
        )
    return "\n".join(lines)


def experience_from_text(text: str) -> list[dict]:
    items = []
    for line in (text or "").splitlines():
        if not line.strip():
            continue
        parts = [part.strip() for part in line.split("|")]
        while len(parts) < 5:
            parts.append("")
        items.append(
            {
                "title": parts[0],
                "company": parts[1],
                "start": parts[2],
                "end": parts[3],
                "bullets": parts[4],
            }
        )
    return items


def projects_to_text(items: list[dict]) -> str:
    return "\n".join(f"{item.get('name') or ''} | {item.get('description') or ''}" for item in items)


def projects_from_text(text: str) -> list[dict]:
    items = []
    for line in (text or "").splitlines():
        if not line.strip():
            continue
        parts = [part.strip() for part in line.split("|", 1)]
        if len(parts) == 1:
            parts.append("")
        items.append({"name": parts[0], "description": parts[1], "skills": ""})
    return items


def profile_from_form(form) -> tuple[dict, bool]:
    """Return the profile and whether the weights were rescaled."""
    profile = empty_profile()
    profile["full_name"] = (form.get("full_name") or "").strip()
    profile["email"] = (form.get("email") or "").strip()
    profile["phone"] = (form.get("phone") or "").strip()
    profile["location"] = (form.get("location") or "").strip()
    profile["headline"] = (form.get("headline") or "").strip()
    profile["summary"] = (form.get("summary") or "").strip()
    profile["skills"] = skills_from_text(form.get("skills") or "")
    profile["education"] = education_from_text(form.get("education") or "")
    profile["experience"] = experience_from_text(form.get("experience") or "")
    profile["projects"] = projects_from_text(form.get("projects") or "")
    weights, rescaled = _weights(form)
    profile["preferences"] = {
        "target_role": (form.get("target_role") or "").strip(),
        "locations": (form.get("locations") or "").strip(),
        "work_type": (form.get("work_type") or "any").strip().lower(),
        "level": (form.get("level") or "any").strip().lower(),
        "notes": (form.get("notes") or "").strip(),
        "weights": weights,
    }
    if profile["preferences"]["work_type"] not in {"any", "remote", "hybrid", "onsite"}:
        profile["preferences"]["work_type"] = "any"
    if profile["preferences"]["level"] not in {"any", "intern", "entry", "mid"}:
        profile["preferences"]["level"] = "any"
    return profile, rescaled


def _weights(form) -> tuple[dict, bool]:
    raw = {}
    for key, field, default in (
        ("skill", "w_skill", DEFAULT_WEIGHTS["skill"]),
        ("semantic", "w_semantic", DEFAULT_WEIGHTS["semantic"]),
        ("preference", "w_preference", DEFAULT_WEIGHTS["preference"]),
    ):
        try:
            raw[key] = max(0.0, float(form.get(field) or default))
        except ValueError:
            raw[key] = default
    total = sum(raw.values())
    rescaled = abs(total - 1) > 0.02
    if total <= 0:
        return dict(DEFAULT_WEIGHTS), True
    return {key: value / total for key, value in raw.items()}, rescaled


def form_defaults(profile: dict | None) -> dict:
    profile = profile or empty_profile()
    prefs = profile.get("preferences") or default_preferences()
    weights = prefs.get("weights") or DEFAULT_WEIGHTS
    return {
        "full_name": profile.get("full_name") or "",
        "email": profile.get("email") or "",
        "phone": profile.get("phone") or "",
        "location": profile.get("location") or "",
        "headline": profile.get("headline") or "",
        "summary": profile.get("summary") or "",
        "skills": skills_to_text(profile.get("skills") or []),
        "education": education_to_text(profile.get("education") or []),
        "experience": experience_to_text(profile.get("experience") or []),
        "projects": projects_to_text(profile.get("projects") or []),
        "target_role": prefs.get("target_role") or "",
        "locations": prefs.get("locations") or "",
        "work_type": prefs.get("work_type") or "any",
        "level": prefs.get("level") or "any",
        "notes": prefs.get("notes") or "",
        "w_skill": f"{float(weights.get('skill', 0.5)):.2f}",
        "w_semantic": f"{float(weights.get('semantic', 0.35)):.2f}",
        "w_preference": f"{float(weights.get('preference', 0.15)):.2f}",
    }
