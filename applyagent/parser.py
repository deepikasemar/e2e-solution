"""Resume reading and section parsing (sections 5.3 and appendix A.1)."""

from __future__ import annotations

import re
from pathlib import Path

from applyagent.skills import extract_skills, normalize_skill_list

HEADERS: dict[str, set[str]] = {
    "summary": {"summary", "objective", "professional summary", "about", "about me", "profile"},
    "education": {"education", "academic background", "academics", "qualification", "qualifications"},
    "skills": {"skills", "technical skills", "core skills", "technologies", "tech stack", "key skills"},
    "experience": {
        "experience",
        "work experience",
        "professional experience",
        "employment",
        "internships",
        "internship",
    },
    "projects": {"projects", "academic projects", "personal projects", "project work", "project"},
}

_EMAIL = re.compile(r"[\w.+-]+@[\w.-]+\.\w+")
_PHONE = re.compile(r"(\+?\d[\d\-\s()]{8,}\d)")
_YEAR = re.compile(r"(?:19|20)\d{2}")


def read_resume(path: str | Path) -> str:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _read_pdf(path)
    if suffix == ".docx":
        return _read_docx(path)
    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="replace")
    raise ValueError("Upload a PDF, DOCX or TXT resume.")


def _read_pdf(path: Path) -> str:
    import pdfplumber

    parts: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            parts.append(page.extract_text() or "")
    return "\n".join(parts).strip()


def _read_docx(path: Path) -> str:
    from docx import Document

    document = Document(str(path))
    lines = [paragraph.text for paragraph in document.paragraphs]
    return "\n".join(lines).strip()


def empty_profile() -> dict:
    return {
        "full_name": "",
        "email": "",
        "phone": "",
        "location": "",
        "headline": "",
        "summary": "",
        "skills": [],
        "education": [],
        "experience": [],
        "projects": [],
        "preferences": default_preferences(),
    }


def default_preferences() -> dict:
    return {
        "target_role": "",
        "locations": "",
        "work_type": "any",
        "level": "any",
        "notes": "",
        "weights": {"skill": 0.50, "semantic": 0.35, "preference": 0.15},
    }


def example_preferences() -> dict:
    prefs = default_preferences()
    prefs.update(
        {
            "target_role": "Python Developer",
            "locations": "Remote, Punjab",
            "work_type": "any",
            "level": "entry",
            "notes": "Entry-level Python roles, remote or in Punjab.",
        }
    )
    return prefs


def parse_resume_text(text: str) -> dict:
    """Build a structured profile. The caller must show it for correction."""
    profile = empty_profile()
    lines = [line.strip() for line in (text or "").replace("\r", "\n").split("\n")]
    lines = [line for line in lines if line]
    if not lines:
        return profile

    profile["full_name"] = lines[0][:80] if "@" not in lines[0] and len(lines[0]) < 60 else ""
    email, phone, location = _contact(lines[:8])
    profile["email"] = email
    profile["phone"] = phone
    profile["location"] = location

    sections = _split_sections(lines)
    summary = " ".join(sections.get("summary", []))
    profile["summary"] = summary
    profile["headline"] = _first_sentence(summary)[:180]

    skill_source = " ".join(sections.get("skills", [])) or text
    # Skills named anywhere in the resume are suggestions. The saved list is
    # what later steps are allowed to use, after the user edits it.
    profile["skills"] = normalize_skill_list(extract_skills(text if sections.get("skills") else skill_source))
    if sections.get("skills"):
        profile["skills"] = normalize_skill_list(extract_skills(text))

    profile["education"] = [_education_line(line) for line in sections.get("education", []) if line]
    profile["experience"] = _parse_experience(sections.get("experience", []))
    profile["projects"] = _parse_projects(sections.get("projects", []))
    return profile


def _contact(lines: list[str]) -> tuple[str, str, str]:
    email = ""
    phone = ""
    location = ""
    blob = "\n".join(lines)
    email_match = _EMAIL.search(blob)
    if email_match:
        email = email_match.group(0)
    phone_match = _PHONE.search(blob)
    if phone_match:
        phone = " ".join(phone_match.group(1).split())
    for line in lines:
        if "|" not in line:
            continue
        for part in (piece.strip() for piece in line.split("|")):
            if not part or "@" in part or _PHONE.search(part):
                continue
            location = part
            break
    return email, phone, location


def _header_name(line: str) -> str | None:
    key = line.strip().rstrip(":").lower()
    if len(key) > 42:
        return None
    for name, aliases in HEADERS.items():
        if key in aliases:
            return name
    return None


def _split_sections(lines: list[str]) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in lines:
        header = _header_name(line)
        if header:
            current = header
            sections.setdefault(current, [])
            continue
        if current:
            sections[current].append(line)
    return sections


def _education_line(line: str) -> dict:
    years = _YEAR.findall(line)
    year = years[-1] if years else ""
    parts = [part.strip() for part in line.split(",") if part.strip()]
    parts = [part for part in parts if not _YEAR.fullmatch(part)]
    if len(parts) >= 2:
        degree = parts[0]
        institution = ", ".join(parts[1:])
    elif parts:
        degree = parts[0]
        institution = ""
    else:
        degree = line
        institution = ""
    return {"degree": degree, "institution": institution, "year": year, "details": ""}


def _parse_experience(lines: list[str]) -> list[dict]:
    entries: list[dict] = []
    current: dict | None = None
    for line in lines:
        bullet = _strip_bullet(line)
        if bullet != line and current is not None:
            current["bullets"] = (current["bullets"] + " " + bullet).strip()
            continue
        if _looks_like_role(line):
            if current:
                entries.append(current)
            current = _role_line(line)
            continue
        if current is not None:
            current["bullets"] = (current["bullets"] + " " + line).strip()
    if current:
        entries.append(current)
    return entries


def _looks_like_role(line: str) -> bool:
    if line.startswith(("-", "•", "*")):
        return False
    if _YEAR.search(line) and "," in line:
        return True
    months = ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")
    lowered = line.lower()
    return "," in line and any(month in lowered for month in months)


def _role_line(line: str) -> dict:
    parts = [part.strip() for part in line.split(",")]
    title = parts[0] if parts else line
    dates = ""
    company_parts: list[str] = []
    if len(parts) >= 2 and (_YEAR.search(parts[-1]) or _looks_like_role(parts[-1]) or "-" in parts[-1]):
        dates = parts[-1]
        company_parts = parts[1:-1]
    else:
        company_parts = parts[1:]
    start, end = _split_dates(dates)
    return {
        "title": title,
        "company": ", ".join(company_parts),
        "start": start,
        "end": end,
        "bullets": "",
    }


def _split_dates(dates: str) -> tuple[str, str]:
    if not dates:
        return "", ""
    pieces = re.split(r"\s+[–—-]\s+|\s+to\s+", dates, maxsplit=1)
    if len(pieces) == 2:
        return pieces[0].strip(), pieces[1].strip()
    return dates.strip(), ""


def _strip_bullet(line: str) -> str:
    return re.sub(r"^[\-\•\*]\s*", "", line).strip()


def _parse_projects(lines: list[str]) -> list[dict]:
    blocks: list[list[str]] = []
    current: list[str] = []
    # Section lines are already split. Treat a short line after a wrapped
    # description as a new project when the previous line ended a sentence
    # and this line has no period and is short — the sample uses one title
    # line plus one description line, separated by the original blank line.
    # Blank lines were removed, so a new project starts when the previous
    # description looks complete and the new line is a short title.
    for line in lines:
        if not current:
            current = [line]
            continue
        previous = current[-1]
        if previous.endswith(".") and len(line.split()) <= 8 and not line.endswith("."):
            blocks.append(current)
            current = [line]
        else:
            current.append(line)
    if current:
        blocks.append(current)
    projects = []
    for block in blocks:
        projects.append({"name": block[0], "description": " ".join(block[1:]).strip(), "skills": ""})
    return projects


def _first_sentence(text: str) -> str:
    text = " ".join(text.split())
    if not text:
        return ""
    match = re.match(r".+?[.]", text)
    return match.group(0) if match else text
