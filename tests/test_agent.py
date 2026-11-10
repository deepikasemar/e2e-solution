import io

import pytest

from applyagent.cleaner import clean_text, dedup_key
from applyagent.documents import text_docx, text_pdf
from applyagent.evaluate import (
    example_profile,
    full_report,
    ndcg_at_k,
    parsing_report,
    precision_at_k,
    ranking_report,
    skill_extraction_report,
)
from applyagent.factcheck import check_documents
from applyagent.generator import build_letter
from applyagent.matcher import preference_score, prepare_job, rank_jobs, skill_score
from applyagent.parser import parse_resume_text, read_resume
from applyagent.seed import JOBS, SAMPLE_RESUME
from applyagent.skills import extract_skills


def test_html_cleaning_strips_tags_links_and_keeps_words():
    raw = "<p>We are hiring a <b>Python Developer</b>! Apply at https://www.example.com. Must know SQL &amp; REST APIs.</p>"
    cleaned = clean_text(raw)
    assert "<" not in cleaned
    assert "https://" not in cleaned
    assert "Python Developer" in cleaned
    assert "REST APIs" in cleaned
    assert dedup_key("Python Developer", "Sutlej Labs") == dedup_key("python  developer", "sutlej labs")


def test_skill_aliases_do_not_split_javascript():
    assert extract_skills("JavaScript and Java") == ["java", "javascript"]
    assert extract_skills("ML and machine learning") == ["machine learning"]
    assert "java" not in extract_skills("A JavaScript internship")


def test_skill_score_formula():
    score, matched, missing = skill_score(["python", "sql", "flask"], ["python", "sql", "docker"])
    assert score == pytest.approx(2 / 3)
    assert matched == ["python", "sql"]
    assert missing == ["docker"]
    assert skill_score(["python"], [])[0] == 0


def test_name_is_not_part_of_the_match_text():
    left = example_profile()
    right = example_profile()
    right["full_name"] = "Someone Else"
    right["email"] = "other@example.com"
    right["phone"] = "000"
    jobs = [prepare_job(job) for job in JOBS]
    a, _ = rank_jobs(left, jobs)
    b, _ = rank_jobs(right, jobs)
    assert [item["score"] for item in a] == pytest.approx([item["score"] for item in b])


def test_example_profile_parsing_and_ranking():
    parsed = parsing_report()
    assert parsed["accuracy"] == 1
    ranking = ranking_report()
    assert ranking["precision_at_5"] >= 0.8
    assert ranking["order"][0]["relevant"]
    skills = skill_extraction_report()
    assert skills["overall"]["f1"] == 1
    report = full_report([])
    assert report["generation"]["passed"]


def test_preference_rewards_punjab_and_remote():
    profile = example_profile()
    remote = {"location": "Remote", "work_type": "remote", "title": "Python Developer", "level": "entry"}
    civil = {"location": "Mumbai", "work_type": "onsite", "title": "Site Engineer", "level": "mid"}
    assert preference_score(profile, remote) > preference_score(profile, civil)


def test_fact_checker_flags_invented_skill_and_years():
    profile = example_profile()
    letter = build_letter(profile, prepare_job(JOBS[0]), ["python", "flask"])
    assert check_documents(profile, "", letter) == []
    flags = check_documents(profile, "", letter + " I have 9 years of experience and I run Kubernetes.")
    kinds = {flag["kind"] for flag in flags}
    assert "skill" in kinds
    assert "experience" in kinds


def test_pdf_and_docx_round_trip(tmp_path):
    pdf_path = tmp_path / "resume.pdf"
    pdf_path.write_bytes(text_pdf(SAMPLE_RESUME))
    assert "aarav.mehta@example.com" in read_resume(pdf_path)
    docx_path = tmp_path / "resume.docx"
    docx_path.write_bytes(text_docx(SAMPLE_RESUME))
    text = read_resume(docx_path)
    assert "Flask" in text
    assert parse_resume_text(text)["email"] == "aarav.mehta@example.com"


def test_metric_helpers():
    assert precision_at_k([1, 0, 1, 0], 2) == 0.5
    assert ndcg_at_k([1, 1], 2) == pytest.approx(1)
    assert ndcg_at_k([1, 0, 1], 2) < 1


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "agent.sqlite"))
    monkeypatch.setenv("DAILY_LIMIT", "2")
    monkeypatch.setenv("SEMANTIC_BACKEND", "tfidf")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    from applyagent.web import create_app

    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def test_end_to_end_review_gate(client):
    home = client.get("/")
    assert home.status_code == 200
    assert b"Apply with the facts" in home.data
    assert client.get("/healthz").json["ok"] is True

    loaded = client.post("/profile/example", follow_redirects=True)
    assert b"Aarav Mehta" in loaded.data

    jobs = client.get("/jobs")
    assert b"Sutlej Labs" in jobs.data
    assert b"missing docker" in jobs.data.lower() or b"missing Docker" in jobs.data

    blocked = client.get("/jobs/s1")
    assert blocked.status_code == 200
    draft = client.post("/jobs/s1/draft", follow_redirects=True)
    assert b"Dear Hiring Team at Sutlej Labs" in draft.data
    assert b"Fact check" in draft.data

    poisoned = client.post(
        "/review/1",
        data={
            "action": "approve",
            "summary": "Aarav Mehta knows Kubernetes.",
            "cover_letter": "Dear Hiring Team at Sutlej Labs,\n\nI administer Kubernetes.\n\nSincerely,\nAarav Mehta",
        },
        follow_redirects=True,
    )
    assert b"unsupported" in poisoned.data.lower()
    packet = client.get("/review/1/packet", follow_redirects=True)
    assert b"Approve the draft" in packet.data

    approved = client.post(
        "/review/1",
        data={
            "action": "approve",
            "summary": "Aarav Mehta — final-year student. Verified skills that overlap this role: python and flask.",
            "cover_letter": "Dear Hiring Team at Sutlej Labs,\n\nI am applying for the Python Developer role. I use python and flask.\n\nSincerely,\nAarav Mehta",
        },
        follow_redirects=True,
    )
    assert b"Approved" in approved.data
    assert client.get("/review/1/packet").status_code == 200

    applied = client.post(
        "/review/1",
        data={
            "action": "apply",
            "summary": "Aarav Mehta — final-year student.",
            "cover_letter": "Dear Hiring Team at Sutlej Labs,\n\nI am applying.\n\nSincerely,\nAarav Mehta",
        },
        follow_redirects=True,
    )
    assert b"Recorded as applied" in applied.data
    tracker = client.get("/tracker")
    assert b"applied" in tracker.data
    csv_body = client.get("/tracker.csv").data.decode()
    assert "Sutlej Labs" in csv_body

    client.post("/jobs/s2/draft", follow_redirects=True)
    client.post(
        "/review/2",
        data={"action": "apply", "summary": "Aarav Mehta.", "cover_letter": "Dear Hiring Team,\n\nI apply.\n\nSincerely,\nAarav Mehta"},
        follow_redirects=True,
    )
    third = client.post("/jobs/s7/draft", follow_redirects=True)
    assert b"Dear Hiring Team" in third.data
    limited = client.post(
        "/review/3",
        data={"action": "apply", "summary": "Aarav Mehta.", "cover_letter": "Dear Hiring Team,\n\nI apply.\n\nSincerely,\nAarav Mehta"},
        follow_redirects=True,
    )
    assert b"limit" in limited.data.lower()

    evaluation = client.get("/evaluate")
    assert b"F1" in evaluation.data
    assert b"Precision" in evaluation.data or b"P@10" in evaluation.data


def test_upload_txt_resume(client):
    response = client.post(
        "/profile/upload",
        data={"resume": (io.BytesIO(SAMPLE_RESUME.encode()), "resume.txt")},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"aarav.mehta@example.com" in response.data
    bad = client.post(
        "/profile/upload",
        data={"resume": (io.BytesIO(b"hello"), "notes.exe")},
        follow_redirects=True,
    )
    assert b"PDF, DOCX or TXT" in bad.data


def test_collect_keeps_sample_when_network_fails(client, monkeypatch):
    def boom(_limit=30):
        raise RuntimeError("offline")

    monkeypatch.setattr("applyagent.collector._remotive", boom)
    monkeypatch.setattr("applyagent.collector._weworkremotely", boom)
    response = client.post("/jobs/collect", follow_redirects=True)
    assert response.status_code == 200
    assert b"could not be reached" in response.data
    assert b"Sutlej Labs" in response.data
