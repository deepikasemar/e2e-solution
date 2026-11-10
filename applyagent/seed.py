"""Bundled sample resume, sample postings and labelled evaluation sets.

Companies and the example student are fictional. They exist so the
prototype runs without a network connection and so ranking metrics have
a fixed answer key.
"""

from __future__ import annotations

SAMPLE_RESUME = """Aarav Mehta
aarav.mehta@example.com | +91 98765 43210 | Mohali, Punjab

Summary
Final-year computer science student seeking an entry-level Python developer role. Interested in remote work or roles in Punjab.

Education
B.Tech Computer Science and Engineering, Sardar Beant Singh State University, 2027
Higher Secondary, Punjab School Education Board, 2023

Skills
Python, SQL, Flask, Machine Learning, Git, Pandas, REST APIs

Experience
Software Intern, Campus Tech Cell, Jun 2025 - Aug 2025
- Built a Flask app for student event registration using Python and SQL.

Projects
Library Desk
Flask and SQL application that tracks book loans for a college library.

Crop Yield Notes
Coursework project using Python and machine learning to compare simple models on a public agriculture dataset.
"""

EXAMPLE_PREFERENCES = {
    "target_role": "Python Developer",
    "locations": "Remote, Punjab",
    "work_type": "any",
    "level": "entry",
    "notes": "Entry-level Python roles, remote or in Punjab.",
    "weights": {"skill": 0.50, "semantic": 0.35, "preference": 0.15},
}

# Relevant to the example Python student: s1–s6. The rest are distractors.
JOBS: list[dict] = [
    {
        "id": "s1",
        "title": "Python Developer",
        "company": "Sutlej Labs",
        "location": "Mohali, Punjab",
        "work_type": "hybrid",
        "level": "entry",
        "salary": "₹5–7 LPA",
        "posted_date": "2026-03-02",
        "url": "https://example.com/jobs/sutlej-labs-python",
        "source": "sample",
        "description": (
            "Sutlej Labs is hiring a Python developer for an internal tools team in Mohali. "
            "You will build Flask services, write SQL queries, and expose REST APIs used by the campus operations group. "
            "Git is used for every change. This is an entry-level role for someone who has already shipped a small Python project."
        ),
    },
    {
        "id": "s2",
        "title": "Junior Machine Learning Engineer",
        "company": "NimbusCart",
        "location": "Remote",
        "work_type": "remote",
        "level": "entry",
        "salary": "₹6–8 LPA",
        "posted_date": "2026-03-04",
        "url": "https://example.com/jobs/nimbuscart-ml",
        "source": "sample",
        "description": (
            "NimbusCart wants a junior machine learning engineer who can work remotely. "
            "The work is in Python, with pandas and scikit-learn on catalogue data, plus SQL to pull training tables. "
            "You will compare simple models and write short notes about what failed. Prior internship experience is useful but not required."
        ),
    },
    {
        "id": "s3",
        "title": "Backend Intern",
        "company": "CampusGrid",
        "location": "Chandigarh",
        "work_type": "onsite",
        "level": "intern",
        "salary": "₹18,000 / month",
        "posted_date": "2026-02-26",
        "url": "https://example.com/jobs/campusgrid-intern",
        "source": "sample",
        "description": (
            "CampusGrid in Chandigarh is offering a backend internship. "
            "Interns write Python and Django views, store records in SQL, and push work through Git. "
            "The internship is onsite and suited to a final-year student who wants an entry into backend work."
        ),
    },
    {
        "id": "s4",
        "title": "Software Engineer",
        "company": "Indus Cloud",
        "location": "Remote, India",
        "work_type": "remote",
        "level": "entry",
        "salary": "₹7–9 LPA",
        "posted_date": "2026-03-06",
        "url": "https://example.com/jobs/indus-cloud-swe",
        "source": "sample",
        "description": (
            "Indus Cloud is hiring a software engineer to extend a remote-first Python platform. "
            "The service exposes REST APIs backed by PostgreSQL. "
            "The team also packages the app with Docker and reviews code in Git. "
            "Familiarity with SQL and Python matters more than years of experience."
        ),
    },
    {
        "id": "s5",
        "title": "Data Analyst",
        "company": "Amberbyte",
        "location": "Amritsar, Punjab",
        "work_type": "onsite",
        "level": "entry",
        "salary": "₹4.5–6 LPA",
        "posted_date": "2026-02-20",
        "url": "https://example.com/jobs/amberbyte-analyst",
        "source": "sample",
        "description": (
            "Amberbyte in Amritsar needs a data analyst for retail reports. "
            "Day to day work is Python, pandas and SQL, with finished tables shared in Excel. "
            "The role is entry level and onsite. You will explain numbers to people who do not write code."
        ),
    },
    {
        "id": "s6",
        "title": "Flask API Developer",
        "company": "ChaiStack",
        "location": "Remote",
        "work_type": "remote",
        "level": "entry",
        "salary": "₹6–8 LPA",
        "posted_date": "2026-03-01",
        "url": "https://example.com/jobs/chaistack-flask",
        "source": "sample",
        "description": (
            "ChaiStack is looking for a Flask API developer who can work remotely. "
            "You will design REST APIs in Python, keep data in SQLite for the first release, and cover the main flows with tests. "
            "A small published project is enough to apply."
        ),
    },
    {
        "id": "s7",
        "title": "Site Engineer",
        "company": "Riverbank Civil",
        "location": "Ludhiana, Punjab",
        "work_type": "onsite",
        "level": "entry",
        "salary": "₹3.5–4.5 LPA",
        "posted_date": "2026-02-18",
        "url": "https://example.com/jobs/riverbank-site",
        "source": "sample",
        "description": (
            "Riverbank Civil needs a site engineer in Ludhiana to supervise concrete pours, check measurements and write daily safety notes. "
            "The work is outdoors on an active construction site. Drawing reading and coordination with masons matter more than software."
        ),
    },
    {
        "id": "s8",
        "title": "Graphic Designer",
        "company": "Lotus Studio",
        "location": "Delhi",
        "work_type": "hybrid",
        "level": "entry",
        "salary": "₹4–5 LPA",
        "posted_date": "2026-02-22",
        "url": "https://example.com/jobs/lotus-design",
        "source": "sample",
        "description": (
            "Lotus Studio is hiring a graphic designer to make campaign layouts in Figma. "
            "The role covers posters, social tiles and simple brand sheets. A portfolio of visual work is required. "
            "This is not a software engineering position."
        ),
    },
    {
        "id": "s9",
        "title": "Accountant",
        "company": "MetroRoute Books",
        "location": "Jalandhar, Punjab",
        "work_type": "onsite",
        "level": "entry",
        "salary": "₹3.6–4.2 LPA",
        "posted_date": "2026-02-11",
        "url": "https://example.com/jobs/metroroute-accounts",
        "source": "sample",
        "description": (
            "MetroRoute Books needs an accountant in Jalandhar to reconcile invoices, file GST returns and keep the cash book current. "
            "Comfort with spreadsheets and tally-style ledgers is expected. The role does not involve building software."
        ),
    },
    {
        "id": "s10",
        "title": "iOS Developer",
        "company": "Himalaya Pay",
        "location": "Remote",
        "work_type": "remote",
        "level": "mid",
        "salary": "₹12–16 LPA",
        "posted_date": "2026-03-03",
        "url": "https://example.com/jobs/himalaya-ios",
        "source": "sample",
        "description": (
            "Himalaya Pay is hiring an iOS developer for a payments app. "
            "The stack is Swift and SwiftUI. You will ship screens, handle offline states and review pull requests with the mobile team. "
            "Two years of app-store releases are expected."
        ),
    },
    {
        "id": "s11",
        "title": "Java Developer",
        "company": "Kaveri Systems",
        "location": "Noida",
        "work_type": "hybrid",
        "level": "entry",
        "salary": "₹5–7 LPA",
        "posted_date": "2026-02-28",
        "url": "https://example.com/jobs/kaveri-java",
        "source": "sample",
        "description": (
            "Kaveri Systems wants a Java developer for a Spring Boot service in Noida. "
            "The service talks to SQL databases and is covered by JUnit tests. "
            "Applicants should be comfortable in Java rather than scripting languages."
        ),
    },
    {
        "id": "s12",
        "title": "Staff Nurse",
        "company": "Lotus Health Ward",
        "location": "Amritsar, Punjab",
        "work_type": "onsite",
        "level": "entry",
        "salary": "₹3–3.8 LPA",
        "posted_date": "2026-02-14",
        "url": "https://example.com/jobs/lotus-nurse",
        "source": "sample",
        "description": (
            "Lotus Health Ward is hiring a staff nurse for rotating ward shifts in Amritsar. "
            "Duties include patient notes, medicine rounds and handover with the duty doctor. "
            "A nursing diploma and registration are required."
        ),
    },
    {
        "id": "s13",
        "title": "Marketing Executive",
        "company": "ChaiStack Growth",
        "location": "Mumbai",
        "work_type": "hybrid",
        "level": "entry",
        "salary": "₹4–5.5 LPA",
        "posted_date": "2026-02-25",
        "url": "https://example.com/jobs/chaistack-marketing",
        "source": "sample",
        "description": (
            "The growth team wants a marketing executive to plan campus visits, write newsletters and track campaign spend. "
            "Clear writing and a driving licence for city travel are useful. The job is based in Mumbai."
        ),
    },
    {
        "id": "s14",
        "title": "DevOps Engineer",
        "company": "Indus Cloud Platform",
        "location": "Remote",
        "work_type": "remote",
        "level": "mid",
        "salary": "₹14–18 LPA",
        "posted_date": "2026-03-05",
        "url": "https://example.com/jobs/indus-devops",
        "source": "sample",
        "description": (
            "Indus Cloud Platform needs a DevOps engineer to run Kubernetes clusters, write Docker build files and manage AWS accounts. "
            "Linux administration and on-call rotation are part of the job. Three years of production support are expected."
        ),
    },
    {
        "id": "s15",
        "title": "Frontend Engineer",
        "company": "NimbusCart Web",
        "location": "Bengaluru",
        "work_type": "hybrid",
        "level": "entry",
        "salary": "₹6–8 LPA",
        "posted_date": "2026-03-07",
        "url": "https://example.com/jobs/nimbuscart-frontend",
        "source": "sample",
        "description": (
            "NimbusCart Web is hiring a frontend engineer in Bengaluru. "
            "The interface is React with JavaScript, HTML and CSS. "
            "You will build product pages and match designs from the design team. Server-side work is handled by another group."
        ),
    },
    {
        "id": "s16",
        "title": "Content Writer",
        "company": "Amberbyte Stories",
        "location": "Remote",
        "work_type": "remote",
        "level": "entry",
        "salary": "₹3.5–4.5 LPA",
        "posted_date": "2026-02-16",
        "url": "https://example.com/jobs/amberbyte-writer",
        "source": "sample",
        "description": (
            "Amberbyte Stories needs a content writer for product explainers and help-centre articles. "
            "The writing is in plain English for shoppers. Samples of published articles are required. Coding is not part of the role."
        ),
    },
]

RELEVANT_JOB_IDS = {"s1", "s2", "s3", "s4", "s5", "s6"}

GOLD_SKILLS = [
    {
        "text": "We need a Python developer who knows Flask and SQL.",
        "skills": ["flask", "python", "sql"],
    },
    {
        "text": "Experience with machine learning, pandas and scikit-learn is required.",
        "skills": ["machine learning", "pandas", "scikit-learn"],
    },
    {
        "text": "The intern will use Java, Spring Boot and REST APIs.",
        "skills": ["java", "rest api", "spring"],
    },
    {
        "text": "Looking for React, JavaScript and CSS. HTML is a plus.",
        "skills": ["css", "html", "javascript", "react"],
    },
    {
        "text": "Must know Docker, Kubernetes and AWS. Linux administration helps.",
        "skills": ["aws", "docker", "kubernetes", "linux"],
    },
    {
        "text": "This role is about site supervision, concrete quality and safety meetings.",
        "skills": [],
    },
]

GOLD_PROFILE = {
    "email": "aarav.mehta@example.com",
    "phone_digits": "919876543210",
    "name": "Aarav Mehta",
    "skills": ["flask", "git", "machine learning", "pandas", "python", "rest api", "sql"],
    "institution": "Sardar Beant Singh State University",
    "project": "Library Desk",
    "employer": "Campus Tech Cell",
}
