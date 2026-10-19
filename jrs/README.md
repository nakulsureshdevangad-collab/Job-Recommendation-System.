# CareerSpring — Job Recommendation & Career Intelligence

A Flask + SQLite student project for profile-based job recommendations, résumé skill organization, skill-gap analysis, learning plans, interview practice, and application tracking.

## Run locally

1. Install Python 3.10 or newer.
2. In this project folder, create and activate a virtual environment:

   ```powershell
   py -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

3. (Recommended) Set a private secret and admin credentials before first launch:

   ```powershell
   $env:SECRET_KEY = "replace-with-a-long-random-value"
   $env:ADMIN_EMAIL = "admin@example.com"
   $env:ADMIN_PASSWORD = "replace-with-a-strong-password"
   py app.py
   ```

4. Open http://127.0.0.1:5000.

The database and demo listings are created automatically on first run. If no admin settings are provided, the local demo account is `admin@career.local` / `Admin@12345`. Change these before using the app outside a local demo. The credentials are used to seed the admin only when the database has no admin account.

## Included modules

- Email/password registration and login, hashed passwords, role checks, CSRF checks, and account deletion.
- Editable career profile, skill deduplication and category grouping.
- Consent-based PDF upload, text extraction, recognized skill suggestions, private download/delete controls. Scanned PDF OCR is not included.
- Searchable demo job data, weighted recommendations, match explanations, job requirements comparison, saved jobs, and relevance feedback.
- Skill gaps, an explainable TF-IDF/cosine text signal combined with weighted profile matching, a rule-based learning roadmap, and a progress tracker.
- Career action plan, sample-data market counts, and résumé section/contact extraction hints.
- Résumé section/contact hints, a basic ATS checklist, editable role-specific text versions and plain-text export.
- Interview question bank and structure-focused practice feedback, skill mini challenges, a skill evidence builder, cover-letter drafting from user-provided evidence, application tracking, and rule-based job warning flags.
- Saved search alerts (checked when opened; no email delivery), a local rules-based career assistant, and an admin CSV import tool with category labels and feedback counts.
- Admin listing management, dataset overview, user counts, and user-submitted job reports. Admin pages do not expose résumé text or user profile details.

## Recommendation score

The transparent score combines skill overlap (45%), role/interests (15%), local TF-IDF cosine similarity (15%), location (12%), experience level (8%), and employment type (5%). It produces guidance for this project only; it is not a probability of being hired. Search is available across title, company, description, skills, location, and other listing fields.

## Data and limitations

The initial listings are sample records with placeholder application links. Replace them with a permitted dataset or verified sources before presenting results as real vacancies. Market insights summarize only the installed dataset. Saved alerts are evaluated against the local dataset when opened; no background scheduler or email delivery is configured. The application does not connect to a live AI provider, job feed, OCR service, learning catalog, voice service, or current immigration source. Interview and mini-challenge feedback measures answer structure, not factual correctness or skill level. Scam checks identify configured warning phrases and cannot determine whether a listing is genuine. Résumé extraction, ATS checks, and generated career content are heuristics and must be reviewed by the user; the cover-letter helper requires real user-provided evidence.

## Project layout

```text
app.py                 Flask routes, SQLite schema, recommendation logic
templates/             Jinja pages
static/                CSS and small browser interactions
uploads/               Private local PDF storage (ignored by Git)
career.db              Created on first start (ignored by Git)
```

For a deployed version, configure HTTPS, a strong `SECRET_KEY`, a production WSGI server, secure cookie settings, backups, rate limiting, and a privacy/retention policy. Do not use the local demo credentials in a public deployment.

### Importing jobs (admin)

Sign in as an admin and open **Dataset tools**. CSV imports require `title` and `company`; the other supported headers are listed on that page. Imported URLs should be reviewed before users follow them. Category labels are currently managed as dataset metadata and are not automatically assigned to each listing.
