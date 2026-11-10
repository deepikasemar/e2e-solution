"""Flask interface for the job application agent."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd
from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)

from applyagent import __version__
from applyagent.collector import collect_live, sample_jobs
from applyagent.config import daily_limit, secret_key
from applyagent.db import (
    APPLIED_STATES,
    STATUSES,
    count_applied_on,
    get_application,
    get_job,
    get_profile,
    init_db,
    list_applications,
    list_jobs,
    save_profile,
    today_key,
    update_application,
    upsert_jobs,
)
from applyagent.documents import text_docx, text_pdf
from applyagent.evaluate import full_report
from applyagent.forms import form_defaults, profile_from_form
from applyagent.matcher import rank_jobs
from applyagent.parser import example_preferences, parse_resume_text, read_resume
from applyagent.pipeline import PipelineError, draft_application, mark_applied, refresh_draft
from applyagent.seed import SAMPLE_RESUME

PUNJAB = ("punjab", "chandigarh", "mohali", "amritsar", "ludhiana", "jalandhar", "gurdaspur", "patiala")


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = secret_key()
    app.config["MAX_CONTENT_LENGTH"] = 6 * 1024 * 1024
    init_db()
    if not list_jobs():
        upsert_jobs(sample_jobs())

    @app.template_filter("pct")
    def pct(value):
        try:
            return int(round(float(value) * 100))
        except (TypeError, ValueError):
            return 0

    @app.context_processor
    def shell():
        return {
            "daily_limit": daily_limit(),
            "applied_today": count_applied_on(),
            "version": __version__,
        }

    @app.get("/healthz")
    def healthz():
        return {"ok": True, "version": __version__}

    @app.get("/")
    def home():
        profile = get_profile()
        applications = list_applications()
        counts: dict[str, int] = {}
        for item in applications:
            counts[item["status"]] = counts.get(item["status"], 0) + 1
        application_total = len(applications)
        steps = [
            {"name": "Profile", "done": bool(profile and profile.get("skills")), "href": url_for("profile")},
            {"name": "Collect", "done": len(list_jobs()) > 0, "href": url_for("jobs")},
            {"name": "Rank", "done": bool(profile and profile.get("skills")), "href": url_for("jobs")},
            {"name": "Draft", "done": len(applications) > 0, "href": url_for("jobs")},
            {"name": "Review", "done": any(item["status"] != "draft" for item in applications), "href": url_for("tracker")},
            {"name": "Approve", "done": any(item["status"] in {"approved", *APPLIED_STATES} for item in applications), "href": url_for("tracker")},
            {"name": "Track", "done": any(item.get("applied_on") for item in applications), "href": url_for("tracker")},
        ]
        return render_template(
            "home.html",
            profile=profile,
            job_count=len(list_jobs()),
            applications=applications[:5],
            application_total=application_total,
            counts=counts,
            steps=steps,
        )

    @app.route("/profile", methods=["GET", "POST"])
    def profile():
        if request.method == "POST":
            saved, rescaled = profile_from_form(request.form)
            save_profile(saved)
            if rescaled:
                flash("Match weights were rescaled so they sum to 1.", "info")
            flash("Profile saved. Later steps will use only these facts.", "success")
            return redirect(url_for("profile"))
        current = get_profile()
        return render_template("profile.html", form=form_defaults(current), profile=current)

    @app.post("/profile/upload")
    def upload_resume():
        upload = request.files.get("resume")
        if not upload or not upload.filename:
            flash("Choose a PDF, DOCX or TXT resume.", "error")
            return redirect(url_for("profile"))
        suffix = Path(upload.filename).suffix.lower()
        if suffix not in {".pdf", ".docx", ".txt", ".md"}:
            flash("Use a PDF, DOCX or TXT file.", "error")
            return redirect(url_for("profile"))
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
            upload.save(handle.name)
            temp_path = handle.name
        try:
            text = read_resume(temp_path)
        except Exception:
            flash("That file could not be read. Try TXT if the PDF is a scan.", "error")
            return redirect(url_for("profile"))
        finally:
            Path(temp_path).unlink(missing_ok=True)
        if not text.strip():
            flash("No selectable text was found. Paste the resume into the form, or export a text-based PDF.", "error")
            return redirect(url_for("profile"))
        parsed = parse_resume_text(text)
        existing = get_profile()
        if existing and (existing.get("preferences") or {}).get("target_role"):
            parsed["preferences"] = existing["preferences"]
        save_profile(parsed)
        flash("Resume read. Check every field before you rank jobs — parsing can miss or mix lines.", "success")
        return redirect(url_for("profile"))

    @app.post("/profile/example")
    def load_example():
        parsed = parse_resume_text(SAMPLE_RESUME)
        parsed["preferences"] = example_preferences()
        save_profile(parsed)
        flash("Loaded the example final-year student. The person and employers are fictional.", "success")
        return redirect(url_for("profile"))

    @app.get("/sample/resume.txt")
    def sample_txt():
        return SAMPLE_RESUME, 200, {"Content-Type": "text/plain; charset=utf-8"}

    @app.get("/sample/resume.pdf")
    def sample_pdf():
        from io import BytesIO

        return send_file(BytesIO(text_pdf(SAMPLE_RESUME)), mimetype="application/pdf", as_attachment=True, download_name="aarav-mehta-resume.pdf")

    @app.get("/sample/resume.docx")
    def sample_docx():
        from io import BytesIO

        return send_file(
            BytesIO(text_docx(SAMPLE_RESUME)),
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            as_attachment=True,
            download_name="aarav-mehta-resume.docx",
        )

    @app.get("/jobs")
    def jobs():
        profile = get_profile()
        stored = list_jobs()
        backend = "not ranked"
        if profile and profile.get("skills"):
            ranked, backend = rank_jobs(profile, stored)
        else:
            ranked = sorted(stored, key=lambda job: job.get("posted_date") or "", reverse=True)
            for job in ranked:
                job.setdefault("score", None)
        for index, job in enumerate(ranked, start=1):
            job["rank"] = index
        shown = [job for job in ranked if _keep_job(job)]
        return render_template(
            "jobs.html",
            jobs=shown,
            total=len(ranked),
            profile=profile,
            backend=backend,
            query=request.args.get("q") or "",
            work=request.args.get("work") or "",
            region=request.args.get("region") or "",
        )

    @app.post("/jobs/collect")
    def collect():
        upsert_jobs(sample_jobs())
        live, reports = collect_live()
        stats = upsert_jobs(live) if live else {"inserted": 0, "updated": 0}
        parts = [f"Sample postings refreshed. Live sources added {stats['inserted']} and updated {stats['updated']}."]
        for report in reports:
            if report["ok"]:
                parts.append(f"{report['source']}: {report['count']} read.")
            else:
                parts.append(f"{report['source']} could not be reached ({report['error']}).")
        flash(" ".join(parts), "info")
        return redirect(url_for("jobs"))

    @app.get("/jobs/<job_id>")
    def job_detail(job_id: str):
        job = get_job(job_id)
        if not job:
            abort(404)
        profile = get_profile()
        ranked_job = None
        position = None
        backend = None
        if profile and profile.get("skills"):
            ranked, backend = rank_jobs(profile, list_jobs())
            for index, item in enumerate(ranked, start=1):
                if item["id"] == job_id:
                    ranked_job = item
                    position = index
                    break
        return render_template(
            "job.html",
            job=ranked_job or job,
            profile=profile,
            position=position,
            total=len(list_jobs()),
            backend=backend,
        )

    @app.post("/jobs/<job_id>/draft")
    def start_draft(job_id: str):
        try:
            application_id = draft_application(job_id)
        except PipelineError as exc:
            flash(str(exc), "error")
            return redirect(url_for("job_detail", job_id=job_id))
        return redirect(url_for("review", application_id=application_id))

    @app.route("/review/<int:application_id>", methods=["GET", "POST"])
    def review(application_id: int):
        application = get_application(application_id)
        if not application:
            abort(404)
        if request.method == "POST":
            return _review_post(application)
        return render_template("review.html", application=application, limit=daily_limit())

    @app.get("/review/<int:application_id>/packet")
    def packet(application_id: int):
        application = get_application(application_id)
        if not application:
            abort(404)
        if application["status"] not in {"approved", *APPLIED_STATES}:
            flash("Approve the draft before opening the prefilled form.", "error")
            return redirect(url_for("review", application_id=application_id))
        return render_template("packet.html", application=application)

    @app.get("/tracker")
    def tracker():
        return render_template("tracker.html", applications=list_applications(), statuses=STATUSES)

    @app.post("/tracker/<int:application_id>/status")
    def tracker_status(application_id: int):
        application = get_application(application_id)
        if not application:
            abort(404)
        status = request.form.get("status") or ""
        if status not in STATUSES:
            abort(400)
        fields = {"status": status}
        if status in APPLIED_STATES and not application.get("applied_on"):
            if count_applied_on() >= daily_limit():
                flash(f"Daily limit of {daily_limit()} is already reached for today (IST).", "error")
                return redirect(url_for("tracker"))
            fields["applied_on"] = today_key()
        if status in {"draft", "approved", "rejected"}:
            fields["applied_on"] = None
        update_application(application_id, **fields)
        flash("Tracker updated.", "success")
        return redirect(url_for("tracker"))

    @app.get("/tracker.csv")
    def tracker_csv():
        rows = []
        for item in list_applications():
            rows.append(
                {
                    "id": item["id"],
                    "company": item["company"],
                    "title": item["title"],
                    "status": item["status"],
                    "applied_on": item.get("applied_on") or "",
                    "rating": item.get("rating") or "",
                    "writer": item.get("writer") or "",
                    "fact_flags": len(item.get("fact_flags") or []),
                    "created_at": item["created_at"],
                }
            )
        frame = pd.DataFrame(rows)
        from flask import Response

        return Response(
            frame.to_csv(index=False),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=applications.csv"},
        )

    @app.get("/evaluate")
    def evaluate():
        report = full_report(list_applications())
        return render_template("evaluate.html", report=report)

    @app.errorhandler(404)
    def missing(_exc):
        return render_template("error.html", title="Not found", message="That page is not in this prototype."), 404

    @app.errorhandler(413)
    def too_large(_exc):
        flash("That file is larger than 6 MB.", "error")
        return redirect(url_for("profile"))

    return app


def _keep_job(job: dict) -> bool:
    query = (request.args.get("q") or "").strip().lower()
    work = (request.args.get("work") or "").strip().lower()
    region = (request.args.get("region") or "").strip().lower()
    if work and job.get("work_type") != work:
        return False
    if region == "punjab":
        haystack = f"{job.get('location') or ''}".lower()
        if not any(token in haystack for token in PUNJAB):
            return False
    if query:
        blob = " ".join(
            [
                job.get("title") or "",
                job.get("company") or "",
                job.get("location") or "",
                " ".join(job.get("skills") or []),
            ]
        ).lower()
        if query not in blob:
            return False
    return True


def _review_post(application: dict):
    action = request.form.get("action") or "save"
    summary = request.form.get("summary") if "summary" in request.form else application["summary"]
    letter = request.form.get("cover_letter") if "cover_letter" in request.form else application["cover_letter"]
    summary = summary or ""
    letter = letter or ""
    if action == "regenerate":
        if application["status"] in APPLIED_STATES:
            flash("This application is already recorded. Start a new draft to regenerate.", "error")
            return redirect(url_for("review", application_id=application["id"]))
        try:
            fresh_id = _regenerate(application)
        except PipelineError as exc:
            flash(str(exc), "error")
            return redirect(url_for("review", application_id=application["id"]))
        flash("A new draft was written from the verified profile.", "success")
        return redirect(url_for("review", application_id=fresh_id))

    application = refresh_draft(application, summary, letter)
    if application["fact_flags"] and application["status"] == "approved":
        update_application(application["id"], status="draft")
        application["status"] = "draft"
    if action == "save":
        if application["status"] == "approved":
            update_application(application["id"], status="draft")
        flash("Draft saved.", "success")
    elif action == "approve":
        if application["fact_flags"] and request.form.get("acknowledge") != "yes":
            flash("The draft has unsupported claims. Edit them out, or tick the box only if the wording is still true.", "error")
            return redirect(url_for("review", application_id=application["id"]))
        update_application(application["id"], status="approved")
        flash("Approved. You can prefill the form next. Nothing has been sent to the employer.", "success")
    elif action == "reject":
        update_application(application["id"], status="rejected", applied_on=None)
        flash("Marked as rejected. It will not count toward today's limit.", "info")
    elif action == "apply":
        if application["status"] in {"draft", "rejected"}:
            if application["fact_flags"] and request.form.get("acknowledge") != "yes":
                flash("Resolve the fact-check flags and approve the draft before recording it.", "error")
                return redirect(url_for("review", application_id=application["id"]))
            update_application(application["id"], status="approved")
        current = get_application(application["id"])
        try:
            mark_applied(current)
        except PipelineError as exc:
            flash(str(exc), "error")
            return redirect(url_for("review", application_id=application["id"]))
        flash("Recorded as applied on this computer. Submit the real form yourself on the employer site.", "success")
    elif action == "rate":
        try:
            rating = int(request.form.get("rating") or 0)
        except ValueError:
            rating = 0
        if rating < 1 or rating > 5:
            flash("Choose a rating from 1 to 5.", "error")
        else:
            update_application(application["id"], rating=rating)
            flash("Rating saved. It is included in the evaluation page.", "success")
    return redirect(url_for("review", application_id=application["id"]))


def _regenerate(application: dict) -> int:
    """Replace draft text by creating the documents again on the same row."""
    from applyagent.db import get_profile
    from applyagent.factcheck import check_documents
    from applyagent.generator import generate_documents
    from applyagent.matcher import rank_jobs
    import time

    profile = get_profile()
    job = get_job(application["job_id"])
    if not profile or not job:
        raise PipelineError("Profile or job is missing, so the draft cannot be regenerated.")
    ranked, backend = rank_jobs(profile, [job])
    match = ranked[0]
    match["backend"] = backend
    started = time.perf_counter()
    summary, letter, writer = generate_documents(profile, job, match["matched_skills"])
    elapsed = int((time.perf_counter() - started) * 1000)
    flags = check_documents(profile, summary, letter)
    from applyagent.pipeline import _public_match, application_packet

    update_application(
        application["id"],
        summary=summary,
        cover_letter=letter,
        writer=writer,
        fact_flags=flags,
        match_json=_public_match(match),
        form_json=application_packet(profile, job, summary, letter),
        generation_ms=elapsed,
        status="draft",
    )
    return int(application["id"])
