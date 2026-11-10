"""Draft a resume summary and cover letter from the verified profile only.

If OPENAI_API_KEY is set, an OpenAI-compatible chat model writes the draft
and the fact checker still runs. Otherwise a template writer uses only
fields the user saved. Either way the user edits and approves the text.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

from applyagent.skills import extract_skills


def generate_documents(profile: dict, job: dict, matched_skills: list[str]) -> tuple[str, str, str]:
    """Return summary, cover letter, and the writer name ('template' or 'llm')."""
    if os.environ.get("OPENAI_API_KEY"):
        try:
            summary, letter = _llm(profile, job)
            return summary, letter, "llm"
        except Exception:
            pass
    summary = build_summary(profile, job, matched_skills)
    letter = build_letter(profile, job, matched_skills)
    return summary, letter, "template"


def profile_facts(profile: dict) -> str:
    lines = []
    if profile.get("full_name"):
        lines.append(f"Name: {profile['full_name']}")
    if profile.get("headline"):
        lines.append(f"Headline: {profile['headline']}")
    if profile.get("summary"):
        lines.append(f"Summary: {profile['summary']}")
    if profile.get("location"):
        lines.append(f"Location: {profile['location']}")
    if profile.get("skills"):
        lines.append("Skills: " + ", ".join(profile["skills"]))
    for item in profile.get("education") or []:
        lines.append(
            "Education: "
            + ", ".join(
                bit
                for bit in (item.get("degree"), item.get("institution"), item.get("year"))
                if bit
            )
        )
    for item in profile.get("experience") or []:
        lines.append(
            f"Experience: {item.get('title', '')} at {item.get('company', '')} "
            f"({item.get('start', '')} - {item.get('end', '')}). {item.get('bullets', '')}"
        )
    for item in profile.get("projects") or []:
        lines.append(f"Project: {item.get('name', '')}. {item.get('description', '')}")
    return "\n".join(lines)


def build_summary(profile: dict, job: dict, matched_skills: list[str]) -> str:
    name = profile.get("full_name") or "Candidate"
    headline = (profile.get("headline") or profile.get("summary") or "Job seeker").strip()
    sentences = [f"{name} — {headline}"]
    education = profile.get("education") or []
    if education:
        item = education[0]
        bits = [item.get("degree"), item.get("institution")]
        edu = ", ".join(bit for bit in bits if bit)
        if item.get("year"):
            edu += f" ({item['year']})"
        if edu:
            sentences.append(f"Education: {edu}.")
    if matched_skills:
        sentences.append(
            f"Verified skills that overlap {job.get('title', 'this role')} at {job.get('company', 'the employer')}: {_join(matched_skills)}."
        )
    elif profile.get("skills"):
        sentences.append(f"Verified skills: {_join(profile['skills'][:8])}.")
    projects = profile.get("projects") or []
    if projects:
        project = _best_project(projects, matched_skills)
        if project.get("name"):
            detail = project.get("description") or ""
            sentences.append(f"Project {project['name']}: {detail}".strip())
    return _tidy(" ".join(sentences))


def build_letter(profile: dict, job: dict, matched_skills: list[str]) -> str:
    name = profile.get("full_name") or "Candidate"
    company = job.get("company") or "the hiring team"
    title = job.get("title") or "the open role"
    paragraphs = [f"Dear Hiring Team at {company},"]
    opening = f"I am writing to apply for the {title} position."
    if profile.get("summary"):
        opening += " " + profile["summary"].strip()
    paragraphs.append(opening)
    if matched_skills:
        paragraphs.append(
            f"From my verified profile, the skills I would use in this role are {_join(matched_skills)}."
        )
    experience = profile.get("experience") or []
    if experience:
        item = experience[0]
        when = ""
        if item.get("start") or item.get("end"):
            when = f" ({item.get('start', '')} – {item.get('end', '')})"
        sentence = (
            f"I worked as {item.get('title') or 'a contributor'} at "
            f"{item.get('company') or 'a previous organisation'}{when}."
        )
        bullet = (item.get("bullets") or "").strip()
        if bullet:
            sentence += " " + bullet.rstrip(".") + "."
        paragraphs.append(sentence)
    projects = profile.get("projects") or []
    if projects:
        project = _best_project(projects, matched_skills)
        if project.get("name"):
            paragraphs.append(f"A related project is {project['name']}: {project.get('description', '')}".strip())
    paragraphs.append(
        "Each point above is taken from my verified profile. I am happy to complete your application form myself and to discuss the role."
    )
    paragraphs.append("Sincerely,\n" + name)
    return "\n\n".join(paragraphs).strip()


def _best_project(projects: list[dict], matched_skills: list[str]) -> dict:
    wanted = set(matched_skills or [])

    def score(project: dict) -> int:
        text = f"{project.get('name', '')} {project.get('description', '')}"
        return len(set(extract_skills(text)) & wanted)

    return max(projects, key=score)


def _join(items: list[str]) -> str:
    items = [item for item in items if item]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + " and " + items[-1]


def _tidy(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _llm(profile: dict, job: dict) -> tuple[str, str]:
    key = os.environ["OPENAI_API_KEY"]
    base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    prompt = (
        "You are helping a job seeker write a short resume summary and a cover letter.\n"
        "Use ONLY the facts in the PROFILE. Do not invent skills, employers, dates, degrees or years of experience.\n"
        "If a requirement is not in the profile, leave it out.\n"
        "Keep a professional tone. The cover letter must be at most 220 words.\n\n"
        f"PROFILE:\n{profile_facts(profile)}\n\n"
        f"JOB:\n{job.get('title')} at {job.get('company')}\n{job.get('description', '')[:3500]}\n\n"
        'Return JSON with keys "summary" and "cover_letter".'
    )
    body = json.dumps(
        {
            "model": model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": "You write truthful job-application drafts and you reply with JSON only."},
                {"role": "user", "content": prompt},
            ],
        }
    ).encode()
    request = urllib.request.Request(
        f"{base}/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Language model request failed ({exc.code}).") from exc
    content = payload["choices"][0]["message"]["content"]
    content = content.strip()
    content = re.sub(r"^```(?:json)?", "", content).strip().rstrip("`").strip()
    parsed = json.loads(content)
    summary = str(parsed.get("summary") or "").strip()
    letter = str(parsed.get("cover_letter") or "").strip()
    if not summary or not letter:
        raise RuntimeError("Language model returned an empty draft.")
    return summary, letter
