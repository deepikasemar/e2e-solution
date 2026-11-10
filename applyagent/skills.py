"""Lexicon and phrase matcher for skill extraction.

Known skills are matched with word boundaries, longest alias first, so
"JavaScript" is not also stored as "Java". Names the lexicon does not
know are left out on purpose: the matcher must not invent skills.
"""

from __future__ import annotations

import re

# Canonical name -> aliases, all lowercase.
_RAW: dict[str, list[str]] = {
    "python": ["python"],
    "sql": ["postgresql", "postgres", "mysql", "sqlite", "sql"],
    "machine learning": ["machine learning", "ml"],
    "deep learning": ["deep learning"],
    "flask": ["flask"],
    "django": ["django"],
    "fastapi": ["fastapi", "fast api"],
    "rest api": ["restful apis", "restful api", "rest apis", "rest api"],
    "git": ["git"],
    "pandas": ["pandas"],
    "numpy": ["numpy"],
    "scikit-learn": ["scikit-learn", "scikit learn", "sklearn"],
    "tensorflow": ["tensorflow"],
    "pytorch": ["pytorch"],
    "nlp": ["natural language processing", "nlp"],
    "spacy": ["spacy"],
    "nltk": ["nltk"],
    "bert": ["sentence-bert", "sentence bert", "bert"],
    "docker": ["docker"],
    "kubernetes": ["kubernetes", "k8s"],
    "aws": ["amazon web services", "aws"],
    "azure": ["azure"],
    "gcp": ["google cloud", "gcp"],
    "linux": ["linux"],
    "java": ["java"],
    "spring": ["spring boot", "spring"],
    "javascript": ["javascript", "js"],
    "typescript": ["typescript"],
    "react": ["react.js", "reactjs", "react"],
    "node.js": ["node.js", "nodejs", "node"],
    "html": ["html"],
    "css": ["css"],
    "mongodb": ["mongodb", "mongo"],
    "redis": ["redis"],
    "excel": ["microsoft excel", "excel"],
    "power bi": ["power bi"],
    "tableau": ["tableau"],
    "figma": ["figma"],
    "swift": ["swiftui", "swift"],
    "kotlin": ["kotlin"],
    "android": ["android"],
    "selenium": ["selenium"],
    "playwright": ["playwright"],
    "jenkins": ["jenkins"],
    "ci/cd": ["ci/cd", "cicd"],
    "graphql": ["graphql"],
    "kafka": ["kafka"],
    "hadoop": ["hadoop"],
    "spark": ["apache spark"],
    "c++": ["c++"],
    "c#": ["c#"],
    "golang": ["golang", "go lang"],
    "php": ["php"],
    "laravel": ["laravel"],
    "ruby": ["ruby on rails", "ruby"],
    "rails": ["ruby on rails"],
    "angular": ["angular"],
    "vue": ["vue.js", "vuejs", "vue"],
    "next.js": ["next.js", "nextjs"],
    "tailwind": ["tailwind css", "tailwind"],
    "bootstrap": ["bootstrap"],
    "oop": ["object oriented programming", "object-oriented programming"],
    "data structures": ["data structures"],
    "algorithms": ["algorithms"],
    "statistics": ["statistics"],
    "dbms": ["dbms"],
    "operating systems": ["operating systems"],
    "computer networks": ["computer networks"],
    "agile": ["agile"],
    "jira": ["jira"],
    "postman": ["postman"],
    "firebase": ["firebase"],
    "streamlit": ["streamlit"],
}

_ALIAS_TO_CANONICAL: list[tuple[str, str]] = sorted(
    ((alias, canonical) for canonical, aliases in _RAW.items() for alias in aliases),
    key=lambda item: len(item[0]),
    reverse=True,
)

_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(rf"(?<![a-z0-9+#.]){re.escape(alias)}(?![a-z0-9+#.])"), canonical)
    for alias, canonical in _ALIAS_TO_CANONICAL
]


def extract_skills(text: str) -> list[str]:
    """Return sorted canonical skills found in text."""
    if not text:
        return []
    lowered = text.lower().replace("–", " ").replace("—", " ")
    # Drop sentence-ending periods, but keep dots inside tokens such as node.js.
    lowered = re.sub(r"\.(?![a-z0-9])", " ", lowered)
    found: list[str] = []
    seen: set[str] = set()
    for pattern, canonical in _PATTERNS:
        if canonical in seen:
            continue
        if pattern.search(lowered):
            seen.add(canonical)
            found.append(canonical)
    return sorted(found)


def normalize_skill_list(items: list[str]) -> list[str]:
    """Map a user-edited skill list onto canonical names, keeping unknown phrases."""
    known = extract_skills(", ".join(items))
    custom: list[str] = []
    known_set = set(known)
    for item in items:
        cleaned = " ".join(item.strip().lower().split())
        if not cleaned:
            continue
        recognised = extract_skills(cleaned)
        if recognised:
            continue
        if cleaned not in known_set:
            custom.append(cleaned)
    return sorted(set(known) | set(custom))
