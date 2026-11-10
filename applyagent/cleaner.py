"""Text cleaning for job descriptions (section 5.4)."""

from __future__ import annotations

import html
import re


_TAG = re.compile(r"<[^>]+>")
_SCRIPT = re.compile(r"(?is)<(script|style).*?>.*?</\1>")
_URL = re.compile(r"https?://\S+|www\.\S+")
_SPACE = re.compile(r"[ \t]+")
_NEWLINES = re.compile(r"\n{3,}")


def clean_text(raw: str) -> str:
    """Strip tags, links and repeated whitespace. Keep the words."""
    text = raw or ""
    text = _SCRIPT.sub(" ", text)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</p>", "\n", text)
    text = _TAG.sub(" ", text)
    text = html.unescape(text)
    text = _URL.sub(" ", text)
    text = text.replace("\r", "\n")
    text = _SPACE.sub(" ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    text = _NEWLINES.sub("\n\n", text)
    return text.strip()


def dedup_key(title: str, company: str) -> str:
    blob = f"{title} {company}".lower()
    blob = re.sub(r"[^a-z0-9]+", " ", blob)
    return " ".join(blob.split())
