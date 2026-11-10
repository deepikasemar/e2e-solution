"""Metrics from chapter 8, computed on the bundled labelled sets and on live tracker rows."""

from __future__ import annotations

import math
import re

from applyagent.factcheck import check_documents
from applyagent.generator import build_letter, build_summary
from applyagent.matcher import prepare_job, rank_jobs
from applyagent.parser import parse_resume_text
from applyagent.seed import EXAMPLE_PREFERENCES, GOLD_PROFILE, GOLD_SKILLS, JOBS, RELEVANT_JOB_IDS, SAMPLE_RESUME
from applyagent.skills import extract_skills


def precision_recall_f1(predicted: set[str], truth: set[str]) -> dict[str, float]:
    tp = len(predicted & truth)
    fp = len(predicted - truth)
    fn = len(truth - predicted)
    precision = tp / (tp + fp) if (tp + fp) else 1.0 if not truth else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    if precision + recall == 0:
        f1 = 0.0
    else:
        f1 = 2 * precision * recall / (precision + recall)
    return {"precision": precision, "recall": recall, "f1": f1, "tp": tp, "fp": fp, "fn": fn}


def skill_extraction_report() -> dict:
    tp = fp = fn = 0
    rows = []
    for item in GOLD_SKILLS:
        predicted = set(extract_skills(item["text"]))
        truth = set(item["skills"])
        scores = precision_recall_f1(predicted, truth)
        tp += scores["tp"]
        fp += scores["fp"]
        fn += scores["fn"]
        rows.append({"text": item["text"], "predicted": sorted(predicted), "truth": sorted(truth), **scores})
    overall = precision_recall_f1_counts(tp, fp, fn)
    return {"overall": overall, "rows": rows}


def precision_recall_f1_counts(tp: int, fp: int, fn: int) -> dict[str, float]:
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    return {"precision": precision, "recall": recall, "f1": f1, "tp": tp, "fp": fp, "fn": fn}


def precision_at_k(relevances: list[int], k: int) -> float:
    if k <= 0:
        return 0.0
    top = relevances[:k]
    return sum(1 for value in top if value) / k


def ndcg_at_k(relevances: list[int], k: int) -> float:
    top = relevances[:k]

    def dcg(values: list[int]) -> float:
        total = 0.0
        for index, relevance in enumerate(values):
            total += (2**relevance - 1) / math.log2(index + 2)
        return total

    ideal = sorted(relevances, reverse=True)[:k]
    ideal_dcg = dcg(ideal)
    if ideal_dcg == 0:
        return 0.0
    return dcg(top) / ideal_dcg


def example_profile() -> dict:
    profile = parse_resume_text(SAMPLE_RESUME)
    profile["preferences"] = dict(EXAMPLE_PREFERENCES)
    return profile


def ranking_report(profile: dict | None = None) -> dict:
    profile = profile or example_profile()
    jobs = [prepare_job(job) for job in JOBS]
    ranked, backend = rank_jobs(profile, jobs)
    relevances = [1 if job["id"] in RELEVANT_JOB_IDS else 0 for job in ranked]
    return {
        "backend": backend,
        "precision_at_5": precision_at_k(relevances, 5),
        "precision_at_10": precision_at_k(relevances, 10),
        "ndcg_at_10": ndcg_at_k(relevances, 10),
        "order": [
            {"id": job["id"], "title": job["title"], "company": job["company"], "relevant": job["id"] in RELEVANT_JOB_IDS, "score": job["score"]}
            for job in ranked
        ],
    }


def parsing_report() -> dict:
    profile = parse_resume_text(SAMPLE_RESUME)
    digits = re.sub(r"\D", "", profile.get("phone") or "")
    checks = {
        "name": profile.get("full_name") == GOLD_PROFILE["name"],
        "email": profile.get("email") == GOLD_PROFILE["email"],
        "phone": digits == GOLD_PROFILE["phone_digits"],
        "skills": profile.get("skills") == GOLD_PROFILE["skills"],
        "education": any(GOLD_PROFILE["institution"] in (item.get("institution") or "") for item in profile.get("education") or []),
        "project": any(item.get("name") == GOLD_PROFILE["project"] for item in profile.get("projects") or []),
        "employer": any(item.get("company") == GOLD_PROFILE["employer"] for item in profile.get("experience") or []),
    }
    correct = sum(1 for passed in checks.values() if passed)
    return {"accuracy": correct / len(checks), "checks": checks, "correct": correct, "total": len(checks), "profile": profile}


def generation_report() -> dict:
    profile = example_profile()
    job = prepare_job(next(item for item in JOBS if item["id"] == "s1"))
    from applyagent.matcher import skill_score

    _, matched, _ = skill_score(profile["skills"], job["skills"])
    summary = build_summary(profile, job, matched)
    letter = build_letter(profile, job, matched)
    flags = check_documents(profile, summary, letter)
    words = len(re.findall(r"\b[\w']+\b", letter))
    poisoned = letter + "\n\nI also administer Kubernetes in production."
    poisoned_flags = check_documents(profile, summary, poisoned)
    return {
        "truthful_flags": len(flags),
        "poisoned_flags": len(poisoned_flags),
        "cover_letter_words": words,
        "passed": len(flags) == 0 and len(poisoned_flags) > 0 and words <= 250,
    }


def tracker_report(applications: list[dict], generation_ms: list[int]) -> dict:
    rated = [item["rating"] for item in applications if item.get("rating")]
    checked = [item for item in applications if item.get("status") != "rejected"]
    clean = [item for item in checked if not item.get("fact_flags")]
    applied = [item for item in applications if item.get("applied_on")]
    avg_generation = (sum(generation_ms) / len(generation_ms) / 1000 / 60) if generation_ms else 0.0
    from applyagent.config import MANUAL_MINUTES, REVIEW_MINUTES

    per_application = REVIEW_MINUTES + avg_generation
    return {
        "applications": len(applications),
        "average_rating": (sum(rated) / len(rated)) if rated else None,
        "rated_count": len(rated),
        "fact_check_pass_rate": (len(clean) / len(checked)) if checked else None,
        "manual_minutes": MANUAL_MINUTES,
        "agent_minutes": per_application,
        "minutes_saved_each": max(0.0, MANUAL_MINUTES - per_application),
        "applied_count": len(applied),
    }


def full_report(applications: list[dict] | None = None) -> dict:
    applications = applications or []
    generation_ms = [item["generation_ms"] for item in applications if item.get("generation_ms")]
    return {
        "parsing": parsing_report(),
        "skills": skill_extraction_report(),
        "ranking": ranking_report(),
        "generation": generation_report(),
        "tracker": tracker_report(applications, generation_ms),
    }
