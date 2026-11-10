# ApplyAgent

The agent turns a resume into a structured profile, collects job postings, ranks them, drafts a summary and cover letter from verified facts, and records an application only after you approve it.

## What you can do

1. Upload a PDF, DOCX or TXT resume, or load the fictional example student from section 5.11.
2. Correct the profile. That saved profile is the only source of facts.
3. Rank openings. The score is `w1 × skill overlap + w2 × cosine similarity + w3 × preference`.
4. Read matching skills and missing skills (for example Docker).
5. Draft a summary and cover letter. A fact check flags skills that are not on the profile.
6. Approve, reject, or edit. Then open a prefilled packet and copy it into the employer form yourself.
7. Track status. A daily limit (India time) caps how many applications you can record.
8. Open **Evaluation** for field accuracy, precision / recall / F1, precision@k, NDCG@10, and your own ratings.

Nothing is submitted to an employer. Name, email and phone are not used in the match score.

## Run locally

Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python wsgi.py
```

Open http://127.0.0.1:43123

Production-style process:

```bash
gunicorn -b 0.0.0.0:43123 --timeout 120 wsgi:app
```

Tests:

```bash
pytest
```

Copy `.env.example` to `.env` only if you want to change limits or add a language-model key. The app runs with no key: drafts are written from the profile by a template, then fact-checked.

## Matching

| Part | Default weight | What it measures |
| --- | --- | --- |
| Skill overlap | 0.50 | Share of the job’s skills that are on your profile |
| Semantic similarity | 0.35 | Cosine similarity of TF-IDF vectors (1–2 word grams) |
| Preference | 0.15 | Target role, location, work type, level |

Set `SEMANTIC_BACKEND=sentence-transformers` and install `sentence-transformers` to use `all-MiniLM-L6-v2` instead of TF-IDF. The formula stays the same. The default is TF-IDF so the app starts without a large model download.

If `OPENAI_API_KEY` is set, drafts are requested from an OpenAI-compatible chat endpoint (`OPENAI_BASE_URL`, `OPENAI_MODEL`). The key is read from the environment and is not written into the database or the page. If the call fails, the template writer is used.

## Jobs

Sixteen labelled sample postings ship with the app so ranking and the demo work offline. **Refresh permitted sources** also tries:

- Remotive’s public software-development API
- We Work Remotely’s programming RSS feed

Duplicates are dropped by normalised title and company. HTML is stripped before storage. If a live source fails, the sample set stays.

## Data

SQLite file: `var/applyagent.sqlite` (or `DATABASE_PATH`). It holds one profile, the jobs, and the tracker. Export the tracker as CSV from the tracker page.

## Deploy

Docker:

```bash
docker compose up --build
```

The compose file stores the database in a volume at `/data`. The service listens on port **43123**. `GET /healthz` returns `{"ok": true}`.

Render: this repo includes `render.yaml` (Docker runtime, health check `/healthz`). On a free instance the SQLite file disappears when the disk is reset; use a persistent disk if applications must survive a restart.

Environment variables:

| Variable | Purpose |
| --- | --- |
| `PORT` | HTTP port, default 43123 |
| `DATABASE_PATH` | SQLite file |
| `DAILY_LIMIT` | Recorded applications per IST day, default 8 |
| `SECRET_KEY` | Flask session key; set a long random value in public hosting |
| `SEMANTIC_BACKEND` | `tfidf` or `sentence-transformers` |
| `OPENAI_API_KEY` | Optional language-model drafts |

## Project map

| Module | Code |
| --- | --- |
| Resume parser | `applyagent/parser.py` |
| Cleaning and skill phrases | `applyagent/cleaner.py`, `applyagent/skills.py` |
| Matching | `applyagent/matcher.py`, `applyagent/embeddings.py` |
| Cover letter and summary | `applyagent/generator.py` |
| Fact check | `applyagent/factcheck.py` |
| Job collector | `applyagent/collector.py` |
| Tracker | `applyagent/db.py` |
| Metrics | `applyagent/evaluate.py` |
| Interface | `applyagent/web.py`, `applyagent/templates/` |

Sample companies and Aarav Mehta are fictional, so the prototype can be demonstrated without applying to real employers.
