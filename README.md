# Boomerang AI — Smart Hiring Reconnect System

An AI-powered HR tool that re-engages high-potential past candidates using Gemini LLM matching and personalized email outreach.

---

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Set environment variables

**Linux / macOS:**
```bash
export GEMINI_API_KEY="your_gemini_api_key_here"
export SMTP_USER="your_gmail@gmail.com"
export SMTP_PASS="your_gmail_app_password"
```

**Windows (CMD):**
```cmd
set GEMINI_API_KEY=your_gemini_api_key_here
set SMTP_USER=your_gmail@gmail.com
set SMTP_PASS=your_gmail_app_password
```

> **Gmail App Password:** Go to Google Account → Security → 2-Step Verification → App Passwords → generate one for "Mail".

### 3. Run the app
```bash
python app.py
```

### 4. Open in browser
```
http://localhost:5000
```

---

## Project Structure

```
boomerang_ai/
├── app.py                  # Flask backend + all routes + AI logic
├── boomerang.db            # SQLite database (auto-created on first run)
├── requirements.txt
├── templates/
│   ├── base.html           # Sidebar layout + navigation
│   ├── dashboard.html      # Stats overview + recent matches
│   ├── candidates.html     # Candidate management
│   ├── jobs.html           # Job postings + trigger AI match
│   ├── matches.html        # Ranked results + email generation
│   └── emails.html         # Email activity log
└── static/
    ├── css/style.css       # Full dark-theme design system
    └── js/main.js          # Modal, toast, animations
```

---

## How to Use

1. **Dashboard** — Overview of stats and recent AI match results
2. **Candidates** — View, add, or remove candidate profiles (12 pre-seeded)
3. **Job Openings** — Post new roles; click **"Run AI Match"** to trigger Gemini LLM scoring
4. **Match Results** — See ranked candidates; click **"Generate"** to create a personalized email; click **"Send"** to dispatch via SMTP
5. **Email Logs** — Full audit trail of all outreach emails and their delivery status

---

## Tech Stack

| Layer     | Technology                    |
|-----------|-------------------------------|
| Backend   | Python 3.10+ / Flask          |
| AI Engine | Google Gemini 1.5 Flash (LLM) |
| Database  | SQLite (via sqlite3)          |
| Email     | SMTP (Gmail / any provider)   |
| Frontend  | HTML5, CSS3, Vanilla JS       |
| Fonts     | Syne + DM Sans (Google Fonts) |

---

## Pre-seeded Data

- **12 candidates** with varied skills, experience, and roles
- **4 job openings** covering Python, React, ML, and DevOps
- Candidate emails rotate between the two specified addresses

---

## Environment Variables Reference

| Variable       | Description                     | Default              |
|----------------|---------------------------------|----------------------|
| GEMINI_API_KEY | Your Gemini API key             | *(required)*         |
| SMTP_HOST      | SMTP server hostname            | smtp.gmail.com       |
| SMTP_PORT      | SMTP port                       | 587                  |
| SMTP_USER      | Sender email address            | *(required for send)*|
| SMTP_PASS      | Email app password              | *(required for send)*|
