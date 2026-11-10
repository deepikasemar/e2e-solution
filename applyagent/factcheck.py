"""Compare a draft with the verified profile and flag unsupported skills."""

from __future__ import annotations

import re

from applyagent.skills import extract_skills

_YEARS = re.compile(r"(\d+)\+?\s+years?")


def check_documents(profile: dict, summary: str, letter: str) -> list[dict]:
    text = f"{summary or ''}\n{letter or ''}"
    verified = set(profile.get("skills") or [])
    flags: list[dict] = []
    for skill in extract_skills(text):
        if skill not in verified:
            flags.append(
                {
                    "kind": "skill",
                    "text": skill,
                    "detail": f"“{skill}” appears in the draft but is not in the verified skill list.",
                }
            )
    claimed = _claimed_years(text)
    if claimed is not None:
        known = _experience_span_years(profile)
        if known is None or claimed > known + 0.5:
            flags.append(
                {
                    "kind": "experience",
                    "text": f"{claimed} years",
                    "detail": "The draft states a length of experience that the saved dates do not support.",
                }
            )
    return flags


def _claimed_years(text: str) -> int | None:
    match = _YEARS.search(text.lower())
    if not match:
        return None
    return int(match.group(1))


def _experience_span_years(profile: dict) -> float | None:
    years = []
    for item in profile.get("experience") or []:
        blob = f"{item.get('start', '')} {item.get('end', '')}"
        found = [int(value) for value in re.findall(r"(?:19|20)\d{2}", blob)]
        if len(found) >= 2:
            years.append(max(found) - min(found))
        elif found:
            years.append(0)
    if not years and not (profile.get("experience") or []):
        return 0.0
    if not years:
        return None
    return float(max(years))
