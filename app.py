import os
import json
import smtplib
import sqlite3
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import google.generativeai as genai
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "TalentBridge-ai-dev-secret-key")

# ── CONFIG ──────────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
SMTP_HOST      = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT      = int(os.environ.get("SMTP_PORT", 587))
SMTP_USER      = os.environ.get("SMTP_USER")
SMTP_PASS      = os.environ.get("SMTP_PASS")
DB_PATH        = "TalentBridge.db"

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

# ── DATABASE INIT ────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT NOT NULL,
            email         TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            company       TEXT,
            created_at    TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS candidates (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT NOT NULL,
            email         TEXT NOT NULL,
            skills        TEXT NOT NULL,
            experience    INTEGER NOT NULL,
            previous_role TEXT NOT NULL,
            resume_text   TEXT
        );

        CREATE TABLE IF NOT EXISTS jobs (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            job_title           TEXT NOT NULL,
            skills_required     TEXT NOT NULL,
            experience_required INTEGER NOT NULL,
            job_description     TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS matches (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id        INTEGER NOT NULL,
            candidate_id  INTEGER NOT NULL,
            match_score   REAL NOT NULL,
            status        TEXT DEFAULT 'Shortlisted',
            FOREIGN KEY (job_id)       REFERENCES jobs(id),
            FOREIGN KEY (candidate_id) REFERENCES candidates(id)
        );

        CREATE TABLE IF NOT EXISTS emails (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id  INTEGER NOT NULL,
            job_id        INTEGER NOT NULL,
            email_subject TEXT NOT NULL,
            email_body    TEXT NOT NULL,
            sent_status   TEXT DEFAULT 'Pending',
            created_at    TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (candidate_id) REFERENCES candidates(id),
            FOREIGN KEY (job_id)       REFERENCES jobs(id)
        );
    """)
    conn.commit()

    # Seed sample candidates only if empty
    if c.execute("SELECT COUNT(*) FROM candidates").fetchone()[0] == 0:
        sample_candidates = [
            ("Arjun Sharma",    "kalikivayeebhumika99@gmail.com", "Python, Flask, SQL, REST APIs",           4, "Backend Developer",         "Experienced backend developer with Flask and PostgreSQL. Built REST APIs for fintech platform."),
            ("Priya Nair",      "kookiesgirl9704@gmail.com",      "React, JavaScript, HTML, CSS, Redux",      3, "Frontend Developer",        "Frontend specialist with React expertise, responsive design, and component libraries."),
            ("Ravi Kumar",      "kalikivayeebhumika99@gmail.com", "Machine Learning, Python, TensorFlow, NLP",5, "ML Engineer",              "Built recommendation systems and NLP pipelines. Strong in model training and evaluation."),
            ("Sneha Reddy",     "kookiesgirl9704@gmail.com",      "Java, Spring Boot, Microservices, Docker", 6, "Java Developer",           "Senior Java developer with microservices architecture and containerization experience."),
            ("Karan Mehta",     "kalikivayeebhumika99@gmail.com", "Data Analysis, SQL, Power BI, Excel",      3, "Data Analyst",             "Proficient in business intelligence, dashboard creation, and SQL query optimization."),
            ("Divya Patel",     "kookiesgirl9704@gmail.com",      "UI/UX, Figma, Adobe XD, Prototyping",     4, "UI/UX Designer",           "Designed mobile-first interfaces for e-commerce and healthcare apps. User research experience."),
            ("Aakash Gupta",    "kalikivayeebhumika99@gmail.com", "DevOps, AWS, Kubernetes, CI/CD, Jenkins",  5, "DevOps Engineer",          "Managed cloud infrastructure for SaaS product. Expert in CI/CD pipelines and monitoring."),
            ("Meera Iyer",      "kookiesgirl9704@gmail.com",      "Python, Django, PostgreSQL, Docker",       4, "Full Stack Developer",     "Full stack developer with Django backend and Vue.js frontend. E-commerce project experience."),
            ("Siddharth Rao",   "kalikivayeebhumika99@gmail.com", "Android, Kotlin, Firebase, REST APIs",     3, "Android Developer",        "Developed three published Android apps with Firebase integration and payment gateway."),
            ("Ananya Singh",    "kookiesgirl9704@gmail.com",      "Salesforce, CRM, Apex, Business Analysis", 5, "Salesforce Developer",     "Certified Salesforce developer with CRM customization and business process automation."),
            ("Rohit Verma",     "kalikivayeebhumika99@gmail.com", "Node.js, Express, MongoDB, GraphQL",       4, "Backend Developer",        "Node.js specialist with GraphQL APIs and MongoDB. Worked in agile startup environment."),
            ("Lakshmi Devi",    "kookiesgirl9704@gmail.com",      "Python, Data Science, Pandas, Scikit-learn",3,"Data Scientist",          "Applied ML models for retail demand forecasting. Strong statistical analysis background."),
        ]
        c.executemany(
            "INSERT INTO candidates (name,email,skills,experience,previous_role,resume_text) VALUES (?,?,?,?,?,?)",
            sample_candidates
        )

    # Seed sample jobs if empty
    if c.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0:
        sample_jobs = [
            ("Senior Python Developer",   "Python, Flask, REST APIs, SQL",          4, "We are looking for a Python developer to build and maintain scalable REST APIs. Experience with Flask and PostgreSQL preferred."),
            ("React Frontend Engineer",   "React, JavaScript, HTML, CSS, Redux",     3, "Join our product team to create delightful user interfaces. You will work on a modern React codebase with TypeScript."),
            ("Machine Learning Engineer", "Machine Learning, Python, NLP, TensorFlow",4,"Develop and deploy ML models for our AI-powered platform. Experience with NLP and model optimization required."),
            ("DevOps / Cloud Engineer",   "AWS, Kubernetes, Docker, CI/CD",          4, "Own our cloud infrastructure on AWS. Set up monitoring, manage Kubernetes clusters, and build reliable CI/CD pipelines."),
        ]
        c.executemany(
            "INSERT INTO jobs (job_title,skills_required,experience_required,job_description) VALUES (?,?,?,?)",
            sample_jobs
        )

    conn.commit()
    conn.close()

# ── AI HELPERS ───────────────────────────────────────────────────────────────
def _fallback_score(candidate: dict, job: dict) -> float:
    """Rule-based fallback scorer used when the AI call fails."""
    import re
    req_skills  = [s.strip().lower() for s in job['skills_required'].split(',')]
    cand_skills = [s.strip().lower() for s in candidate['skills'].split(',')]

    # Skill overlap (60% weight)
    matched = sum(
        1 for rs in req_skills
        if any(rs in cs or cs in rs for cs in cand_skills)
    )
    skill_score = (matched / max(len(req_skills), 1)) * 60

    # Experience match (25% weight)
    req_exp  = int(job.get('experience_required', 0))
    cand_exp = int(candidate.get('experience', 0))
    if cand_exp >= req_exp:
        exp_score = 25
    elif cand_exp >= req_exp - 1:
        exp_score = 15
    else:
        exp_score = max(0, 10 - (req_exp - cand_exp) * 3)

    # Role title similarity (15% weight)
    prev_role  = candidate.get('previous_role', '').lower()
    job_title  = job.get('job_title', '').lower()
    role_words = set(re.split(r'\W+', job_title)) & set(re.split(r'\W+', prev_role))
    role_score = min(15, len(role_words) * 7)

    return round(min(skill_score + exp_score + role_score, 100), 1)


def ai_match_score(candidate: dict, job: dict) -> float:
    import re
    prompt = f"""You are a senior technical recruiter. Score how well this candidate fits the job.

JOB:
Title: {job['job_title']}
Required Skills: {job['skills_required']}
Experience Required: {job['experience_required']} years
Description: {job['job_description']}

CANDIDATE:
Name: {candidate['name']}
Skills: {candidate['skills']}
Experience: {candidate['experience']} years
Previous Role: {candidate['previous_role']}
Resume Summary: {candidate['resume_text']}

Evaluate skill overlap, experience match, and role relevance.
Reply with ONLY a single integer between 0 and 100. Nothing else."""

    try:
        resp = model.generate_content(prompt)
        raw  = resp.text.strip()

        # Try direct parse first
        try:
            score = float(raw)
            return min(max(score, 0), 100)
        except ValueError:
            pass

        # Extract first number found in response
        numbers = re.findall(r'\b(\d{1,3})\b', raw)
        for n in numbers:
            val = float(n)
            if 0 <= val <= 100:
                return val

        # If Gemini returned something but we can't parse it, use fallback
        print(f"[WARN] Could not parse Gemini score from: {repr(raw)[:80]}")
        return _fallback_score(candidate, job)

    except Exception as e:
        print(f"[ERROR] Gemini API call failed: {e}. Using fallback scorer.")
        return _fallback_score(candidate, job)


def ai_generate_email(candidate: dict, job: dict, score: float) -> dict:
    prompt = f"""
Write a short, professional, warm HR outreach email to re-engage this candidate for a new job opportunity.

CANDIDATE: {candidate['name']}
JOB TITLE: {job['job_title']}
COMPANY: TalentBridge AI (fictional tech company)
MATCH SCORE: {score:.0f}/100
CANDIDATE SKILLS: {candidate['skills']}

Guidelines:
- Tone: professional yet friendly
- The body must be EXACTLY 5-6 sentences total, nothing more
- Greet the candidate by name, mention the job title and 1-2 relevant skills, and end with a clear call-to-action to reply if interested
- Sign off with "Best regards, TalentBridge AI HR Team"
- Do NOT use placeholders like [Name] — use actual values
- Return valid JSON with exactly two keys: "subject" and "body"
- No markdown, no code fences, just raw JSON
"""
    try:
        resp = model.generate_content(prompt)
        raw = resp.text.strip()
        # Strip possible markdown fences
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw.strip())
        return {"subject": data.get("subject", "Exciting Opportunity for You"),
                "body":    data.get("body", "We have an exciting opportunity...")}
    except Exception as e:
        return {"subject": f"New Opportunity: {job['job_title']}",
                "body":    f"Dear {candidate['name']},\n\nI hope you're doing well. We have an exciting new opportunity for you as a {job['job_title']} here at TalentBridge AI. Based on your background, your skills in {candidate['skills']} make you a strong match for this role. We'd love to share more details about the position and discuss how it aligns with your career goals. If you're interested, simply reply to this email and we'll set up a quick call.\n\nBest regards,\nTalentBridge AI HR Team"}


def send_email_smtp(to_email: str, subject: str, body: str) -> bool:
    try:
        msg = MIMEMultipart()
        msg["From"]    = SMTP_USER
        msg["To"]      = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, to_email, msg.as_string())
        return True
    except Exception:
        return False

# ── AUTH HELPERS ─────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"error": "unauthorized"}), 401
            return redirect(url_for("signin"))
        return f(*args, **kwargs)
    return wrapper

# ── PUBLIC / AUTH ROUTES ───────────────────────────────────────────────────────
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name     = request.form.get("name", "").strip()
        email    = request.form.get("email", "").strip().lower()
        company  = request.form.get("company", "").strip()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm_password", "")

        error = None
        if not name or not email or not password:
            error = "Please fill in all required fields."
        elif password != confirm:
            error = "Passwords do not match."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."

        if not error:
            conn = get_db()
            existing = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
            if existing:
                error = "An account with this email already exists."
            else:
                conn.execute(
                    "INSERT INTO users (name,email,password_hash,company) VALUES (?,?,?,?)",
                    (name, email, generate_password_hash(password), company)
                )
                conn.commit()
                user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
                session["user_id"]   = user["id"]
                session["user_name"] = user["name"]
                conn.close()
                return redirect(url_for("home"))
            conn.close()

        return render_template("signup.html", error=error, form=request.form)

    return render_template("signup.html", error=None, form={})

@app.route("/signin", methods=["GET", "POST"])
def signin():
    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"]   = user["id"]
            session["user_name"] = user["name"]
            return redirect(url_for("dashboard"))

        return render_template("signin.html", error="Invalid email or password.", form=request.form)

    return render_template("signin.html", error=None, form={})

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

# ── ROUTES ───────────────────────────────────────────────────────────────────

@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_db()
    stats = {
        "candidates": conn.execute("SELECT COUNT(*) FROM candidates").fetchone()[0],
        "jobs":        conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0],
        "matches":     conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0],
        "emails_sent": conn.execute("SELECT COUNT(*) FROM emails WHERE sent_status='Sent'").fetchone()[0],
    }
    recent_matches = conn.execute("""
        SELECT m.match_score, m.status,
               c.name AS cname, c.skills AS cskills,
               j.job_title
        FROM matches m
        JOIN candidates c ON c.id = m.candidate_id
        JOIN jobs j       ON j.id = m.job_id
        ORDER BY m.match_score DESC LIMIT 8
    """).fetchall()
    conn.close()
    return render_template("dashboard.html", stats=stats, recent_matches=recent_matches)

# ── Candidates ────────────────────────────────────────────────────────────────
@app.route("/candidates")
@login_required
def candidates():
    conn    = get_db()
    rows    = conn.execute("SELECT * FROM candidates ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("candidates.html", candidates=rows)

@app.route("/candidates/add", methods=["POST"])
@login_required
def add_candidate():
    d = request.form
    conn = get_db()
    conn.execute(
        "INSERT INTO candidates (name,email,skills,experience,previous_role,resume_text) VALUES (?,?,?,?,?,?)",
        (d["name"], d["email"], d["skills"], int(d["experience"]), d["previous_role"], d.get("resume_text",""))
    )
    conn.commit(); conn.close()
    return redirect(url_for("candidates"))

@app.route("/candidates/delete/<int:cid>", methods=["POST"])
@login_required
def delete_candidate(cid):
    conn = get_db()
    conn.execute("DELETE FROM candidates WHERE id=?", (cid,))
    conn.commit(); conn.close()
    return redirect(url_for("candidates"))

# ── Jobs ──────────────────────────────────────────────────────────────────────
@app.route("/jobs")
@login_required
def jobs():
    conn = get_db()
    rows = conn.execute("SELECT * FROM jobs ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("jobs.html", jobs=rows)

@app.route("/jobs/add", methods=["POST"])
@login_required
def add_job():
    d = request.form
    conn = get_db()
    conn.execute(
        "INSERT INTO jobs (job_title,skills_required,experience_required,job_description) VALUES (?,?,?,?)",
        (d["job_title"], d["skills_required"], int(d["experience_required"]), d["job_description"])
    )
    conn.commit(); conn.close()
    return redirect(url_for("jobs"))

@app.route("/jobs/delete/<int:jid>", methods=["POST"])
@login_required
def delete_job(jid):
    conn = get_db()
    conn.execute("DELETE FROM jobs WHERE id=?", (jid,))
    conn.commit(); conn.close()
    return redirect(url_for("jobs"))

# ── Matching ──────────────────────────────────────────────────────────────────
@app.route("/match/<int:job_id>", methods=["POST"])
@login_required
def run_match(job_id):
    conn = get_db()
    job  = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    candidates_all = conn.execute("SELECT * FROM candidates").fetchall()

    # Remove old matches for this job
    conn.execute("DELETE FROM matches WHERE job_id=?", (job_id,))
    conn.commit()

    results = []
    for cand in candidates_all:
        score = ai_match_score(dict(cand), dict(job))
        status = "Shortlisted" if score >= 50 else "Not Selected"
        conn.execute(
            "INSERT INTO matches (job_id,candidate_id,match_score,status) VALUES (?,?,?,?)",
            (job_id, cand["id"], score, status)
        )
        results.append({"name": cand["name"], "score": score, "status": status})

    conn.commit(); conn.close()
    return jsonify({"success": True, "results": sorted(results, key=lambda x: -x["score"])})

@app.route("/matches/<int:job_id>")
@login_required
def view_matches(job_id):
    conn = get_db()
    job  = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    matches = conn.execute("""
        SELECT m.id AS mid, m.match_score, m.status,
               c.id AS cid, c.name, c.email, c.skills, c.experience, c.previous_role,
               e.id AS email_id, e.sent_status
        FROM matches m
        JOIN candidates c ON c.id = m.candidate_id
        LEFT JOIN emails e ON e.candidate_id=c.id AND e.job_id=m.job_id
        WHERE m.job_id=?
        ORDER BY m.match_score DESC
    """, (job_id,)).fetchall()
    conn.close()
    return render_template("matches.html", job=job, matches=matches)

# ── Email ─────────────────────────────────────────────────────────────────────
@app.route("/email/generate", methods=["POST"])
@login_required
def generate_email():
    data  = request.json
    conn  = get_db()
    cand  = conn.execute("SELECT * FROM candidates WHERE id=?", (data["candidate_id"],)).fetchone()
    job   = conn.execute("SELECT * FROM jobs WHERE id=?", (data["job_id"],)).fetchone()
    score = conn.execute(
        "SELECT match_score FROM matches WHERE candidate_id=? AND job_id=?",
        (data["candidate_id"], data["job_id"])
    ).fetchone()
    conn.close()

    result = ai_generate_email(dict(cand), dict(job), score["match_score"] if score else 0)

    conn = get_db()
    # Upsert: delete existing draft, insert new
    conn.execute("DELETE FROM emails WHERE candidate_id=? AND job_id=? AND sent_status='Pending'",
                 (data["candidate_id"], data["job_id"]))
    cur = conn.execute(
        "INSERT INTO emails (candidate_id,job_id,email_subject,email_body,sent_status) VALUES (?,?,?,?,?)",
        (data["candidate_id"], data["job_id"], result["subject"], result["body"], "Pending")
    )
    email_id = cur.lastrowid
    conn.commit(); conn.close()

    return jsonify({"success": True, "email_id": email_id,
                    "subject": result["subject"], "body": result["body"]})

@app.route("/email/send/<int:email_id>", methods=["POST"])
@login_required
def send_email_route(email_id):
    conn  = get_db()
    email = conn.execute("SELECT * FROM emails WHERE id=?", (email_id,)).fetchone()
    cand  = conn.execute("SELECT * FROM candidates WHERE id=?", (email["candidate_id"],)).fetchone()

    ok = send_email_smtp(cand["email"], email["email_subject"], email["email_body"])
    status = "Sent" if ok else "Failed"
    conn.execute("UPDATE emails SET sent_status=? WHERE id=?", (status, email_id))
    conn.commit(); conn.close()

    return jsonify({"success": ok, "status": status})

@app.route("/emails")
@login_required
def emails_log():
    conn = get_db()
    rows = conn.execute("""
        SELECT e.*, c.name AS cname, c.email AS cemail, j.job_title
        FROM emails e
        JOIN candidates c ON c.id=e.candidate_id
        JOIN jobs j       ON j.id=e.job_id
        ORDER BY e.created_at DESC
    """).fetchall()
    conn.close()
    return render_template("emails.html", emails=rows)

@app.route("/emails/delete/<int:email_id>", methods=["POST"])
@login_required
def delete_email(email_id):
    conn = get_db()
    conn.execute("DELETE FROM emails WHERE id=?", (email_id,))
    conn.commit(); conn.close()
    return redirect(url_for("emails_log"))

def ai_generate_poster(job: dict) -> dict:
    prompt = f"""You are a professional HR copywriter. Create content for a corporate job hiring poster.

JOB TITLE: {job['job_title']}
REQUIRED SKILLS: {job['skills_required']}
EXPERIENCE REQUIRED: {job['experience_required']} years
JOB DESCRIPTION: {job['job_description']}

Generate the following for this poster. Return ONLY raw JSON, no markdown, no code fences.
{{
  "tagline": "A punchy 6-10 word headline that excites candidates (e.g. 'Shape the Future of AI — Join Our Team')",
  "about_role": "2 sentences describing what the candidate will do. Professional, energetic tone.",
  "key_responsibilities": ["responsibility 1", "responsibility 2", "responsibility 3", "responsibility 4"],
  "perks": ["perk 1", "perk 2", "perk 3"],
  "apply_cta": "A short call-to-action line ending with an email like careers@talentbridge.ai"
}}"""
    try:
        resp = model.generate_content(prompt)
        raw = resp.text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw.strip())
        return data
    except Exception as e:
        return {
            "tagline": f"Join Us as a {job['job_title']} — Shape What's Next",
            "about_role": f"We are looking for a talented {job['job_title']} to join our growing team. You will work on exciting projects and make a real impact.",
            "key_responsibilities": [
                f"Design and develop solutions using {job['skills_required'].split(',')[0].strip()}",
                "Collaborate with cross-functional teams to deliver high-quality work",
                "Contribute to architecture decisions and technical strategy",
                "Mentor junior team members and champion best practices"
            ],
            "perks": ["Competitive salary & equity", "Flexible remote-friendly work", "Health & wellness benefits"],
            "apply_cta": f"Send your resume to careers@talentbridge.ai"
        }


def ai_translate_poster(poster_data: dict, job: dict, lang: str) -> dict:
    lang_names = {"hi": "Hindi", "te": "Telugu", "ta": "Tamil", "es": "Spanish"}
    target = lang_names.get(lang, "English")

    # Build explicit per-item instructions so the model cannot skip any
    resp_lines = "\n".join(
        f'  "key_responsibilities[{i}]": "{r}"'
        for i, r in enumerate(poster_data.get("key_responsibilities", []))
    )
    perk_lines = "\n".join(
        f'  "perks[{i}]": "{p}"'
        for i, p in enumerate(poster_data.get("perks", []))
    )

    job_title = job.get("job_title", "")
    location = job.get("location", "")

    prompt = f"""You are an expert bilingual HR copywriter. Your task is to translate a job hiring poster into {target}.

TRANSLATE EVERY SINGLE FIELD COMPLETELY into {target}. Do NOT leave any English words except:
- Company name: "TalentBridge AI" (keep as-is)
- Email addresses, URLs, phone numbers (keep as-is)
- Technical skill names like Python, React, SQL, Excel (keep as-is)

FIELDS TO TRANSLATE:
1. tagline: "{poster_data.get('tagline', '')}"
2. about_role: "{poster_data.get('about_role', '')}"
3. Key Responsibilities (translate EVERY bullet point fully into {target}):
{resp_lines}
4. Requirements/Perks (translate EVERY bullet point fully into {target}):
{perk_lines}
5. apply_cta: "{poster_data.get('apply_cta', '')}"
6. job_title: "{job_title}"
7. location: "{location}"

Return ONLY a raw JSON object with NO markdown, NO code fences, NO preamble.
Every string value must be in {target} script/language.
JSON structure must be exactly:
{{
  "tagline": "...",
  "about_role": "...",
  "key_responsibilities": ["...", "...", ...],
  "perks": ["...", "...", ...],
  "apply_cta": "...",
  "job_title": "...",
  "location": "..."
}}"""
    try:
        resp = model.generate_content(prompt)
        raw = resp.text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw.strip())
        # Validate all lists are translated (same count as original)
        if len(data.get("key_responsibilities", [])) == 0:
            data["key_responsibilities"] = poster_data.get("key_responsibilities", [])
        if len(data.get("perks", [])) == 0:
            data["perks"] = poster_data.get("perks", [])
        # Fallback for job_title and location if missing
        if not data.get("job_title"):
            data["job_title"] = job_title
        if not data.get("location"):
            data["location"] = location
        return data
    except Exception:
        return poster_data


@app.route("/poster/translate-ajax", methods=["POST"])
@login_required
def translate_poster_ajax():
    payload = request.get_json(force=True)
    lang = payload.get("lang", "en")
    poster_data = payload.get("poster_data", {})
    job = payload.get("job", {})
    if lang == "en":
        return jsonify(poster_data)
    translated = ai_translate_poster(poster_data, job, lang)
    return jsonify(translated)


@app.route("/poster")
@login_required
def poster():
    conn = get_db()
    jobs_list = conn.execute("SELECT id, job_title FROM jobs ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("poster.html", jobs=jobs_list, poster_data=None, selected_job=None)


@app.route("/poster/generate", methods=["POST"])
@login_required
def generate_poster():
    job_id = int(request.form.get("job_id", 0))
    conn = get_db()
    job = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    jobs_list = conn.execute("SELECT id, job_title FROM jobs ORDER BY id DESC").fetchall()
    conn.close()
    if not job:
        return redirect(url_for("poster"))
    poster_data = ai_generate_poster(dict(job))
    return render_template("poster.html", jobs=jobs_list, poster_data=poster_data, selected_job=dict(job))


# ── RESUME SCORE vs JD ───────────────────────────────────────────────────────

def extract_pdf_text(file_bytes: bytes) -> str:
    """Extract plain text from PDF bytes using PyMuPDF."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        text = "\n".join(page.get_text() for page in doc)
        doc.close()
        return text.strip()
    except Exception as e:
        return ""


def ai_score_resume(resume_text: str, job: dict) -> dict:
    prompt = f"""You are an expert ATS (Applicant Tracking System) and senior HR analyst.
Analyze the resume against the job description and return a detailed scoring report.

JOB DETAILS:
- Title: {job['job_title']}
- Required Skills: {job['skills_required']}
- Experience Required: {job['experience_required']} years
- Job Description: {job['job_description']}

RESUME TEXT:
{resume_text[:4000]}

Score the resume on these 5 dimensions (0-100 each):
1. skills_match - How well do the candidate's skills match the required skills?
2. experience_match - Does experience level match what is required?
3. education_match - Is educational background appropriate for the role?
4. keyword_match - How many relevant JD keywords appear in the resume?
5. overall_fit - Overall suitability for this role

Also provide:
- matched_skills: list of required skills the candidate HAS (max 8)
- missing_skills: list of required skills the candidate is MISSING (max 8)
- strengths: list of 3 specific strengths from the resume for this role
- gaps: list of 3 specific gaps or concerns
- recommendation: one of "Strong Hire", "Consider", "Needs Development", "Not Suitable"
- summary: 2 sentence summary of the candidate fit

Return ONLY raw JSON, no markdown, no code fences:
{{
  "overall_score": <0-100 integer>,
  "skills_match": <0-100>,
  "experience_match": <0-100>,
  "education_match": <0-100>,
  "keyword_match": <0-100>,
  "overall_fit": <0-100>,
  "matched_skills": ["skill1", ...],
  "missing_skills": ["skill1", ...],
  "strengths": ["strength1", "strength2", "strength3"],
  "gaps": ["gap1", "gap2", "gap3"],
  "recommendation": "...",
  "summary": "..."
}}"""
    try:
        resp = model.generate_content(prompt)
        raw = resp.text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except Exception as e:
        return {
            "overall_score": 0, "skills_match": 0, "experience_match": 0,
            "education_match": 0, "keyword_match": 0, "overall_fit": 0,
            "matched_skills": [], "missing_skills": [],
            "strengths": ["Could not analyze"], "gaps": ["PDF parsing failed"],
            "recommendation": "Error", "summary": f"Analysis failed: {str(e)}"
        }


@app.route("/resume-score")
@login_required
def resume_score():
    conn = get_db()
    jobs_list = conn.execute("SELECT id, job_title FROM jobs ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("resume_score.html", jobs=jobs_list, result=None, selected_job=None, candidate_name="")


@app.route("/resume-score/analyze", methods=["POST"])
@login_required
def analyze_resume():
    job_id = int(request.form.get("job_id", 0))
    candidate_name  = request.form.get("candidate_name", "Candidate").strip()
    candidate_email = request.form.get("candidate_email", "").strip()
    resume_file     = request.files.get("resume_pdf")

    conn = get_db()
    job = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    jobs_list = conn.execute("SELECT id, job_title FROM jobs ORDER BY id DESC").fetchall()
    conn.close()

    if not job or not resume_file:
        return redirect(url_for("resume_score"))

    file_bytes  = resume_file.read()
    resume_text = extract_pdf_text(file_bytes)

    if not resume_text:
        return render_template("resume_score.html", jobs=jobs_list, result=None,
                               selected_job=dict(job), candidate_name=candidate_name,
                               candidate_email=candidate_email,
                               error="Could not extract text from PDF. Please ensure it is a text-based PDF.")

    result = ai_score_resume(resume_text, dict(job))
    return render_template("resume_score.html", jobs=jobs_list, result=result,
                           selected_job=dict(job), candidate_name=candidate_name,
                           candidate_email=candidate_email, error=None)


@app.route("/resume-score/send-email", methods=["POST"])
@login_required
def send_resume_score_email():
    job_id          = int(request.form.get("job_id", 0))
    candidate_name  = request.form.get("candidate_name", "Candidate").strip()
    candidate_email = request.form.get("candidate_email", "").strip()
    overall_score   = int(request.form.get("overall_score", 0))
    matched_skills  = request.form.get("matched_skills", "")

    conn = get_db()
    job       = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    jobs_list = conn.execute("SELECT id, job_title FROM jobs ORDER BY id DESC").fetchall()
    conn.close()

    if not job or not candidate_email:
        return redirect(url_for("resume_score"))

    # Build a candidate-like dict so we can reuse ai_generate_email
    candidate_dict = {
        "name":   candidate_name,
        "email":  candidate_email,
        "skills": matched_skills
    }

    # Generate personalised email via Gemini (same as existing email flow)
    email_content = ai_generate_email(candidate_dict, dict(job), overall_score)
    subject = email_content["subject"]
    body    = email_content["body"]

    # Send via SMTP
    sent_ok = send_email_smtp(candidate_email, subject, body)
    status  = "Sent" if sent_ok else "Failed"

    # Save to emails log — use candidate_id=0 for external candidates
    # Add a virtual candidate row if not present so FK doesn't break
    conn = get_db()
    existing = conn.execute(
        "SELECT id FROM candidates WHERE email=?", (candidate_email,)
    ).fetchone()

    if existing:
        cand_id = existing["id"]
    else:
        cur = conn.execute(
            "INSERT INTO candidates (name, email, skills, experience, previous_role, resume_text) VALUES (?,?,?,?,?,?)",
            (candidate_name, candidate_email, matched_skills, 0, "External Applicant",
             f"Scored {overall_score}% against {dict(job)['job_title']}")
        )
        cand_id = cur.lastrowid

    conn.execute(
        "INSERT INTO emails (candidate_id, job_id, email_subject, email_body, sent_status) VALUES (?,?,?,?,?)",
        (cand_id, job_id, subject, body, status)
    )
    conn.commit()
    conn.close()

    flash_msg = f"✅ Email {'sent' if sent_ok else 'generated (SMTP failed — check .env)'} to {candidate_email}"
    return render_template("resume_score.html",
                           jobs=jobs_list, result=None,
                           selected_job=dict(job),
                           candidate_name=candidate_name,
                           candidate_email=candidate_email,
                           error=None,
                           email_sent=sent_ok,
                           email_status=flash_msg)


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
