"""Semantic similarity.

Default backend is TF-IDF cosine similarity, which runs locally with no
model download. Set SEMANTIC_BACKEND=sentence-transformers to use
all-MiniLM-L6-v2 as described in section 5.6.2. Both backends return a
score in [0, 1] for the same formula.
"""

from __future__ import annotations

import os

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

_MODEL = None


def semantic_scores(profile_text: str, job_texts: list[str]) -> tuple[list[float], str]:
    if not job_texts:
        return [], active_backend_name()
    backend = os.environ.get("SEMANTIC_BACKEND", "tfidf").strip().lower() or "tfidf"
    if backend in {"sentence-transformers", "minilm", "auto"}:
        try:
            return _sentence_scores(profile_text, job_texts), "sentence-transformers:all-MiniLM-L6-v2"
        except Exception:
            if backend != "auto":
                raise
    return _tfidf_scores(profile_text, job_texts), "tf-idf"


def active_backend_name() -> str:
    backend = os.environ.get("SEMANTIC_BACKEND", "tfidf").strip().lower() or "tfidf"
    if backend in {"sentence-transformers", "minilm"}:
        return "sentence-transformers:all-MiniLM-L6-v2"
    return "tf-idf"


def _tfidf_scores(profile_text: str, job_texts: list[str]) -> list[float]:
    documents = [profile_text or "empty profile", *(text or "empty job" for text in job_texts)]
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
    try:
        matrix = vectorizer.fit_transform(documents)
    except ValueError:
        return [0.0 for _ in job_texts]
    scores = cosine_similarity(matrix[0], matrix[1:]).ravel()
    return [float(min(1.0, max(0.0, score))) for score in scores]


def _sentence_scores(profile_text: str, job_texts: list[str]) -> list[float]:
    model = _load_model()
    from sentence_transformers import util

    profile_vector = model.encode(profile_text or "empty profile", convert_to_tensor=True)
    job_vectors = model.encode([text or "empty job" for text in job_texts], convert_to_tensor=True)
    scores = util.cos_sim(profile_vector, job_vectors)[0].tolist()
    return [float(min(1.0, max(0.0, score))) for score in scores]


def _load_model():
    global _MODEL
    if _MODEL is None:
        from sentence_transformers import SentenceTransformer

        name = os.environ.get("SENTENCE_MODEL", "all-MiniLM-L6-v2")
        _MODEL = SentenceTransformer(name)
    return _MODEL
