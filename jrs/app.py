"""Career intelligence and job recommendation application."""
import io
import csv
import math
import os
import random
import re
import secrets
import sqlite3
from collections import Counter
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path

from flask import (Flask, abort, flash, g, redirect, render_template, request,
                   send_file, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
app = Flask(__name__)
app.config.update(SECRET_KEY=os.environ.get("SECRET_KEY", "dev-change-this-key"),
                  MAX_CONTENT_LENGTH=8 * 1024 * 1024, DATABASE=str(BASE_DIR / "career.db"))

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL, password TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'user', created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS profiles(user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE, full_name TEXT DEFAULT '', headline TEXT DEFAULT '', education TEXT DEFAULT '', experience_years REAL DEFAULT 0, technical_skills TEXT DEFAULT '', soft_skills TEXT DEFAULT '', interests TEXT DEFAULT '', preferred_roles TEXT DEFAULT '', preferred_location TEXT DEFAULT '', experience_level TEXT DEFAULT 'Entry-level', employment_type TEXT DEFAULT 'Any', career_goal TEXT DEFAULT '', country TEXT DEFAULT 'India', resume_text TEXT DEFAULT '', resume_filename TEXT DEFAULT '', resume_consent INTEGER DEFAULT 0, updated_at TEXT);
CREATE TABLE IF NOT EXISTS jobs(id INTEGER PRIMARY KEY, title TEXT NOT NULL, company TEXT NOT NULL, location TEXT DEFAULT '', employment_type TEXT DEFAULT 'Full-time', experience_level TEXT DEFAULT 'Entry-level', qualification TEXT DEFAULT '', description TEXT DEFAULT '', skills TEXT DEFAULT '', apply_url TEXT DEFAULT '', salary TEXT DEFAULT '', created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS saved_jobs(user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, job_id INTEGER REFERENCES jobs(id) ON DELETE CASCADE, created_at TEXT NOT NULL, PRIMARY KEY(user_id,job_id));
CREATE TABLE IF NOT EXISTS applications(id INTEGER PRIMARY KEY, user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, job_id INTEGER REFERENCES jobs(id) ON DELETE SET NULL, company TEXT NOT NULL, title TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Saved', applied_date TEXT, follow_up TEXT, notes TEXT DEFAULT '', created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS feedback(id INTEGER PRIMARY KEY, user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, job_id INTEGER REFERENCES jobs(id) ON DELETE CASCADE, rating TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(user_id,job_id));
CREATE TABLE IF NOT EXISTS learning_items(id INTEGER PRIMARY KEY, user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, skill TEXT NOT NULL, priority TEXT DEFAULT 'Medium', resource TEXT DEFAULT '', status TEXT DEFAULT 'Pending', created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS interview_sessions(id INTEGER PRIMARY KEY, user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, role TEXT, question TEXT, answer TEXT DEFAULT '', feedback TEXT DEFAULT '', score INTEGER DEFAULT 0, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS reports(id INTEGER PRIMARY KEY, user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, job_id INTEGER REFERENCES jobs(id) ON DELETE SET NULL, reason TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS resume_versions(id INTEGER PRIMARY KEY, user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, title TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS skill_evidence(id INTEGER PRIMARY KEY, user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, skill TEXT NOT NULL, evidence_type TEXT NOT NULL, detail TEXT NOT NULL, url TEXT DEFAULT '', created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS challenge_attempts(id INTEGER PRIMARY KEY, user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, skill TEXT NOT NULL, prompt TEXT NOT NULL, answer TEXT NOT NULL, score INTEGER NOT NULL, feedback TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS job_alerts(id INTEGER PRIMARY KEY, user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, query TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS job_categories(id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, description TEXT DEFAULT '');
"""

SAMPLE_JOBS = [
 ("Python Developer Intern","Bright Labs","Bengaluru, India","Internship","Internship","BCA/BSc/BE or equivalent","Build APIs, write tests and work with a product team.","Python, Flask, SQL, Git","https://example.com/jobs/python-intern","₹15,000–25,000/month"),
 ("Junior Data Analyst","Northstar Analytics","Remote, India","Full-time","Entry-level","Bachelor's degree","Clean datasets, create dashboards and communicate insights.","SQL, Excel, Python, Power BI, Statistics","https://example.com/jobs/data-analyst","₹4–7 LPA"),
 ("Frontend Developer","Pixel Foundry","Pune, India","Full-time","Entry-level","Bachelor's degree or equivalent","Create accessible responsive web interfaces.","HTML, CSS, JavaScript, React, Git","https://example.com/jobs/frontend","₹5–8 LPA"),
 ("Java Software Engineer","Orbit Systems","Hyderabad, India","Full-time","Mid-level","Bachelor's degree in Computer Science","Develop services and collaborate on code reviews.","Java, Spring Boot, SQL, REST, Docker","https://example.com/jobs/java","₹9–15 LPA"),
 ("QA Automation Trainee","QualityWorks","Chennai, India","Full-time","Fresher","Any graduate","Create test cases and automate browser testing.","Software Testing, Selenium, Python, SQL","https://example.com/jobs/qa","₹3–5 LPA"),
 ("Cloud Support Associate","Skyward Cloud","Remote, India","Full-time","Entry-level","Bachelor's degree or certification","Help customers troubleshoot cloud deployments.","Linux, AWS, Networking, Python, Communication","https://example.com/jobs/cloud","₹5–8 LPA"),
 ("Product Design Intern","Cedar Studio","Mumbai, India","Internship","Internship","Portfolio required","Support user research, wireframes and interface design.","Figma, UX Research, Prototyping, Communication","https://example.com/jobs/design","₹12,000–20,000/month"),
 ("Business Analyst","Cobalt Consulting","Delhi, India","Full-time","Mid-level","Bachelor's degree","Translate business needs into measurable requirements.","Excel, SQL, Communication, Requirements Analysis","https://example.com/jobs/ba","₹8–12 LPA"),
 ("Machine Learning Trainee","OpenTrail AI","Remote, India","Internship","Internship","BSc/BCA/BE or equivalent","Prepare datasets and prototype supervised learning models.","Python, pandas, scikit-learn, Statistics, SQL","https://example.com/jobs/ml","₹18,000/month"),
 ("Full Stack Developer","Riverstone Tech","Jaipur, India","Full-time","Entry-level","Bachelor's degree or equivalent","Build and maintain web applications across the stack.","JavaScript, React, Flask, SQL, REST, Git","https://example.com/jobs/fullstack","₹6–10 LPA"),
]

def db():
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db

@app.teardown_appcontext
def close_db(_exc):
    conn = g.pop("db", None)
    if conn is not None: conn.close()

def init_db():
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.executescript(SCHEMA)
    if conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0:
        now = datetime.utcnow().isoformat()
        conn.executemany("INSERT INTO jobs(title,company,location,employment_type,experience_level,qualification,description,skills,apply_url,salary,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)", [(*j, now) for j in SAMPLE_JOBS])
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@career.local")
    admin_password = os.environ.get("ADMIN_PASSWORD", "Admin@12345")
    if not conn.execute("SELECT 1 FROM users WHERE role='admin'").fetchone():
        conn.execute("INSERT OR IGNORE INTO users(email,password,role,created_at) VALUES(?,?,?,?)", (admin_email.lower(), generate_password_hash(admin_password), "admin", datetime.utcnow().isoformat()))
    conn.commit(); conn.close()

def current_user():
    if "user_id" not in session: return None
    return db().execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()

def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not current_user(): flash("Please sign in to continue.", "info"); return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapped

def admin_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user: return redirect(url_for("login"))
        if user["role"] != "admin": abort(403)
        return fn(*args, **kwargs)
    return wrapped

@app.before_request
def csrf_guard():
    if request.method == "POST":
        token = session.get("csrf_token")
        supplied = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
        if not token or not supplied or not secrets.compare_digest(token, supplied): abort(400, "Invalid security token. Refresh and try again.")

@app.context_processor
def inject_globals():
    if "csrf_token" not in session: session["csrf_token"] = secrets.token_urlsafe(32)
    return {"current_user": current_user(), "csrf_token": session["csrf_token"], "year": datetime.now().year, "parse_skills": parse_skills, "categorize": categorize}

def parse_skills(value):
    if isinstance(value, (list,tuple,set)): parts = value
    else: parts = re.split(r"[,;\n|]+", value or "")
    seen, out = set(), []
    for part in parts:
        skill = re.sub(r"\s+", " ", str(part)).strip()
        key = skill.casefold()
        if skill and key not in seen: seen.add(key); out.append(skill)
    return out

SKILL_GROUPS = {
 "Programming languages": ["python","java","javascript","typescript","c++","c#","php","ruby","go","kotlin","swift"],
 "Web development": ["html","css","javascript","typescript","react","angular","vue","flask","django","node.js","rest","api"],
 "Data and analytics": ["sql","excel","power bi","tableau","pandas","statistics","scikit-learn","machine learning","data analysis"],
 "Database": ["sql","mysql","postgresql","sqlite","mongodb","oracle"],
 "Cloud and DevOps": ["aws","azure","gcp","docker","kubernetes","linux","git","ci/cd"],
 "Testing": ["software testing","selenium","pytest","junit","automation testing"],
 "Design": ["figma","ux research","prototyping","ui design"],
 "Soft skills": ["communication","teamwork","leadership","problem solving","adaptability","time management"]}

def categorize(skills):
    groups = {k: [] for k in SKILL_GROUPS}
    for skill in skills:
        found = [group for group, terms in SKILL_GROUPS.items() if skill.casefold() in terms]
        groups[found[0] if found else "Other"] = groups.get(found[0] if found else "Other", []) + [skill]
    return {k:v for k,v in groups.items() if v}

def profile(user_id=None):
    user_id = user_id or session.get("user_id")
    row = db().execute("SELECT * FROM profiles WHERE user_id=?", (user_id,)).fetchone()
    return dict(row) if row else {"user_id":user_id,"full_name":"","headline":"","education":"","experience_years":0,"technical_skills":"","soft_skills":"","interests":"","preferred_roles":"","preferred_location":"","experience_level":"Entry-level","employment_type":"Any","career_goal":"","country":"India","resume_text":"","resume_filename":"","resume_consent":0}

def score_job(p, job):
    user_skills = {s.casefold() for s in parse_skills(p.get("technical_skills", "") + "," + p.get("soft_skills", ""))}
    required = parse_skills(job["skills"])
    matched = [s for s in required if s.casefold() in user_skills]
    missing = [s for s in required if s.casefold() not in user_skills]
    skill_score = len(matched)/len(required) if required else 0
    text = " ".join([p.get("interests", ""), p.get("preferred_roles", ""), p.get("career_goal", "")]).casefold()
    role_score = 1.0 if job["title"].casefold() in text else (0.65 if any(w in text for w in job["title"].casefold().split() if len(w)>3) else 0.25)
    location_score = 1.0 if not p.get("preferred_location") or p["preferred_location"].casefold() in job["location"].casefold() or "remote" in job["location"].casefold() else 0.15
    exp_score = 1.0 if p.get("experience_level", "Entry-level").casefold() in job["experience_level"].casefold() or job["experience_level"] in ("Fresher","Internship") and float(p.get("experience_years") or 0)<1 else 0.45
    type_score = 1.0 if p.get("employment_type", "Any") in ("Any",job["employment_type"]) else 0.2
    text = " ".join([p.get("interests", ""), p.get("preferred_roles", ""), p.get("career_goal", ""), p.get("headline", "")])
    semantic = tfidf_similarity(text, job_document(job))
    score = round(100*(.45*skill_score+.15*semantic+.15*role_score+.12*location_score+.08*exp_score+.05*type_score))
    reasons = []
    if matched: reasons.append("Skills match: " + ", ".join(matched))
    if role_score>.5: reasons.append("Role relates to your stated interests")
    if location_score>.5: reasons.append("Fits your location preference or is remote")
    if semantic>.12: reasons.append(f"Role description has relevant terms (TF-IDF similarity {round(semantic*100)}%)")
    return score, matched, missing, reasons

STOP_WORDS={"the","and","for","with","from","this","that","your","you","our","are","will","have","has","job","role","work","team","using","use","build","create","support","to","of","in","a","an","on","be","as","or","by","is","we","their","they","at","it","can","who","what","how"}
def tokens(text):
    return [w for w in re.findall(r"[a-z0-9+#.]+",(text or "").casefold()) if len(w)>1 and w not in STOP_WORDS]

def job_document(job):
    return " ".join(str(job[k] or "") for k in ("title","description","skills","qualification"))

def tfidf_similarity(left, right):
    """Small-corpus TF-IDF cosine similarity, used as an explainable local signal."""
    a,b=Counter(tokens(left)),Counter(tokens(right))
    if not a or not b: return 0.0
    all_terms=set(a)|set(b)
    # Two-document inverse frequency keeps shared terms useful while downweighting common words.
    idf={t:1+math.log(3/(1+(t in a)+(t in b))) for t in all_terms}
    vec_a={t:count*idf[t] for t,count in a.items()}
    vec_b={t:count*idf[t] for t,count in b.items()}
    dot=sum(vec_a.get(t,0)*vec_b.get(t,0) for t in all_terms)
    norm_a=math.sqrt(sum(x*x for x in vec_a.values())); norm_b=math.sqrt(sum(x*x for x in vec_b.values()))
    return dot/(norm_a*norm_b) if norm_a and norm_b else 0.0

def recommendations(p, query=""):
    jobs = db().execute("SELECT * FROM jobs ORDER BY id DESC").fetchall()
    q = query.casefold().strip()
    results=[]
    for job in jobs:
        if q and q not in " ".join(str(job[k]) for k in ("title","company","location","description","skills","experience_level","qualification","employment_type")).casefold(): continue
        score, matched, missing, reasons = score_job(p,job)
        results.append({"job":job,"score":score,"matched":matched,"missing":missing,"reasons":reasons})
    return sorted(results,key=lambda x:(x["score"],x["job"]["id"]),reverse=True)

def save_profile(user_id, form):
    fields = {k:(form.get(k) or "").strip() for k in ["full_name","headline","education","technical_skills","soft_skills","interests","preferred_roles","preferred_location","experience_level","employment_type","career_goal","country"]}
    fields["technical_skills"] = ", ".join(parse_skills(fields["technical_skills"]))
    fields["soft_skills"] = ", ".join(parse_skills(fields["soft_skills"]))
    try: fields["experience_years"] = max(0,min(60,float(form.get("experience_years") or 0)))
    except ValueError: fields["experience_years"] = 0
    old=profile(user_id); fields["resume_text"]=old.get("resume_text",""); fields["resume_filename"]=old.get("resume_filename",""); fields["resume_consent"]=old.get("resume_consent",0)
    fields["updated_at"]=datetime.utcnow().isoformat()
    keys=list(fields)
    db().execute(f"INSERT INTO profiles(user_id,{','.join(keys)}) VALUES(?,{','.join('?' for _ in keys)}) ON CONFLICT(user_id) DO UPDATE SET {','.join(k+'=excluded.'+k for k in keys)}", [user_id]+[fields[k] for k in keys]); db().commit()

def extract_pdf(data):
    try:
        from pypdf import PdfReader
        reader=PdfReader(io.BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages)[:50000]
    except ImportError: raise RuntimeError("PDF text extraction needs pypdf. Install dependencies from requirements.txt.")
    except Exception as exc: raise RuntimeError("Could not read this PDF. Try a text-based PDF file.") from exc

@app.route("/")
def index():
    if not current_user(): return render_template("landing.html")
    return redirect(url_for("dashboard"))

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method=="POST":
        email=request.form.get("email","").strip().lower(); password=request.form.get("password","")
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+",email): flash("Enter a valid email address.","error")
        elif len(password)<8: flash("Use a password with at least 8 characters.","error")
        else:
            try:
                cur=db().execute("INSERT INTO users(email,password,created_at) VALUES(?,?,?)",(email,generate_password_hash(password),datetime.utcnow().isoformat())); db().execute("INSERT INTO profiles(user_id,updated_at) VALUES(?,?)",(cur.lastrowid,datetime.utcnow().isoformat())); db().commit(); session.clear(); session["user_id"]=cur.lastrowid; flash("Account created. Add your profile to get started.","success"); return redirect(url_for("profile_page"))
            except sqlite3.IntegrityError: flash("An account with that email already exists.","error")
    return render_template("auth.html",mode="register")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        user=db().execute("SELECT * FROM users WHERE email=?",(request.form.get("email","").strip().lower(),)).fetchone()
        if user and check_password_hash(user["password"],request.form.get("password","")):
            session.clear(); session["user_id"]=user["id"]; flash("Welcome back.","success"); return redirect(url_for("admin" if user["role"]=="admin" else "dashboard"))
        flash("Email or password is incorrect.","error")
    return render_template("auth.html",mode="login")

@app.post("/logout")
def logout(): session.clear(); flash("You have signed out.","info"); return redirect(url_for("index"))

@app.route("/dashboard")
@login_required
def dashboard():
    p=profile(); recs=recommendations(p)[:4]; uid=session["user_id"]
    counts={"saved":db().execute("SELECT COUNT(*) FROM saved_jobs WHERE user_id=?",(uid,)).fetchone()[0],"applications":db().execute("SELECT COUNT(*) FROM applications WHERE user_id=?",(uid,)).fetchone()[0],"learning":db().execute("SELECT COUNT(*) FROM learning_items WHERE user_id=? AND status='Completed'",(uid,)).fetchone()[0]}
    apps=db().execute("SELECT status,COUNT(*) n FROM applications WHERE user_id=? GROUP BY status",(uid,)).fetchall()
    readiness=round(sum(bool(p.get(k)) for k in ["full_name","education","technical_skills","preferred_roles","career_goal"])*20)
    return render_template("dashboard.html",p=p,recs=recs,counts=counts,apps=apps,readiness=readiness,skills=parse_skills(p["technical_skills"]),learning=db().execute("SELECT * FROM learning_items WHERE user_id=? ORDER BY id DESC LIMIT 5",(uid,)).fetchall())

@app.route("/profile",methods=["GET","POST"])
@login_required
def profile_page():
    if request.method=="POST":
        save_profile(session["user_id"],request.form); flash("Profile saved. Recommendations will update from your preferences.","success"); return redirect(url_for("profile_page"))
    return render_template("profile.html",p=profile())

@app.route("/resume",methods=["GET","POST"])
@login_required
def resume():
    uid=session["user_id"]
    if request.method=="POST":
        if request.form.get("action")=="delete":
            p=profile(); (UPLOAD_DIR/secure_filename(p.get("resume_filename", ""))).unlink(missing_ok=True) if p.get("resume_filename") else None
            db().execute("UPDATE profiles SET resume_text='',resume_filename='',resume_consent=0 WHERE user_id=?",(uid,)); db().commit(); flash("Resume deleted from your profile.","success"); return redirect(url_for("resume"))
        file=request.files.get("resume_file")
        if not request.form.get("consent"): flash("Please confirm consent before processing your resume.","error")
        elif not file or not file.filename.lower().endswith(".pdf"): flash("Upload a PDF resume.","error")
        else:
            try:
                data=file.read(); text=extract_pdf(data)
                if not text.strip(): raise RuntimeError("No selectable text found. Scanned PDFs need OCR, which is not enabled in this version.")
                safe=secure_filename(f"{uid}_{file.filename}"); (UPLOAD_DIR/safe).write_bytes(data)
                prev=profile(); (UPLOAD_DIR/secure_filename(prev.get("resume_filename", ""))).unlink(missing_ok=True) if prev.get("resume_filename") and prev["resume_filename"]!=safe else None
                db().execute("UPDATE profiles SET resume_text=?,resume_filename=?,resume_consent=1,updated_at=? WHERE user_id=?",(text,safe,datetime.utcnow().isoformat(),uid)); db().commit()
                known={term.title():term for terms in SKILL_GROUPS.values() for term in terms}
                found=[]
                for term in known:
                    if re.search(r"(?<!\w)"+re.escape(term)+r"(?!\w)",text,re.I) and term.casefold() not in {x.casefold() for x in found}: found.append(term)
                flash(f"Resume analyzed. Found {len(found)} recognized skills. Review and add them to your profile manually.","success"); return redirect(url_for("resume",found=",".join(found)))
            except RuntimeError as exc: flash(str(exc),"error")
    p=profile(); found=parse_skills(request.args.get("found","")); text=p.get("resume_text","")
    extracted=extract_resume_sections(text) if text else {}
    return render_template("resume.html",p=p,found=found,preview=text[:4000],extracted=extracted)

@app.route("/resume/insights")
@login_required
def resume_insights():
    p=profile(); text=p.get("resume_text","")
    if not text: flash("Upload and analyze a PDF first.","info"); return redirect(url_for("resume"))
    known={term.title():term for terms in SKILL_GROUPS.values() for term in terms}
    found=[term for term in known if re.search(r"(?<!\w)"+re.escape(term)+r"(?!\w)",text,re.I)]
    return render_template("resume_insights.html",extracted=extract_resume_sections(text),found=found,preview=text[:4000])

def extract_resume_sections(text):
    lines=[line.strip(" •\t-") for line in (text or "").splitlines() if line.strip()]
    headings={"education":["education","academics"],"experience":["experience","employment","work history"],"projects":["projects","project experience"],"certifications":["certifications","certificates","licenses"]}
    found={}
    for kind,labels in headings.items():
        for i,line in enumerate(lines):
            if line.casefold().rstrip(":") in labels:
                found[kind]="\n".join(lines[i+1:i+5])[:700]
                break
    found["email"]=(re.findall(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}",text,re.I) or [])[:3]
    found["phone"]=(re.findall(r"(?:\+?\d[\d ()-]{7,}\d)",text) or [])[:3]
    found["dates"]=len(re.findall(r"\b(?:19|20)\d{2}\b",text))
    return found

@app.route("/resume/download")
@login_required
def resume_download():
    p=profile(); filename=p.get("resume_filename",""); path=UPLOAD_DIR/secure_filename(filename)
    if not filename or not path.exists(): abort(404)
    return send_file(path,as_attachment=True,download_name="resume.pdf",mimetype="application/pdf")

@app.route("/resume/versions",methods=["GET","POST"])
@login_required
def resume_versions():
    uid=session["user_id"]; p=profile()
    if request.method=="POST":
        action=request.form.get("action")
        if action=="save":
            title=request.form.get("title","").strip() or "Resume version"
            content=request.form.get("content","").strip()
            if content: db().execute("INSERT INTO resume_versions(user_id,title,content,created_at) VALUES(?,?,?,?)",(uid,title[:100],content[:30000],datetime.utcnow().isoformat())); db().commit(); flash("Resume version saved.","success")
            else: flash("Add resume content before saving a version.","error")
        elif action=="delete": db().execute("DELETE FROM resume_versions WHERE id=? AND user_id=?",(request.form.get("id",type=int),uid)); db().commit()
        return redirect(url_for("resume_versions"))
    selected=request.args.get("id",type=int)
    version=db().execute("SELECT * FROM resume_versions WHERE id=? AND user_id=?",(selected,uid)).fetchone() if selected else None
    content=version["content"] if version else "\n".join(x for x in [p["full_name"],p["headline"],p["preferred_location"],"\nSUMMARY\n"+p["career_goal"],"\nEDUCATION\n"+p["education"],"\nSKILLS\n"+p["technical_skills"]+(", "+p["soft_skills"] if p["soft_skills"] else "")] if x)
    return render_template("resume_versions.html",versions=db().execute("SELECT * FROM resume_versions WHERE user_id=? ORDER BY id DESC",(uid,)).fetchall(),content=content,version=version)

@app.route("/resume/versions/<int:version_id>/download")
@login_required
def resume_version_download(version_id):
    version=db().execute("SELECT * FROM resume_versions WHERE id=? AND user_id=?",(version_id,session["user_id"])).fetchone()
    if not version: abort(404)
    return send_file(io.BytesIO(version["content"].encode("utf-8")),as_attachment=True,download_name=secure_filename(version["title"])+".txt",mimetype="text/plain; charset=utf-8")

@app.route("/ats",methods=["GET","POST"])
@login_required
def ats_checker():
    p=profile(); text=p.get("resume_text",""); job_id=request.values.get("job_id",type=int); job=db().execute("SELECT * FROM jobs WHERE id=?",(job_id,)).fetchone() if job_id else None
    checks=[]; score=0
    if text:
        checks=[("Contact details",bool(re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}",text)),"Add a professional email address."),("Recognizable section headings",bool(re.search(r"(?im)^\s*(experience|education|skills|projects)\s*$",text)),"Use clear section headings such as Experience, Education, Skills, and Projects."),("Readable length",len(text.split())>=100,"Add enough detail to show relevant work, projects, or education."),("Dates present",bool(re.search(r"\b(?:19|20)\d{2}\b",text)),"Use consistent dates for education and experience."),("Bullet structure",bool(re.search(r"(?m)^\s*[•*-]\s+",text)),"Use concise bullets for responsibilities and achievements."),("Role keywords",bool(job and any(t.casefold() in text.casefold() for t in parse_skills(job["skills"]))),"Add role keywords only when they accurately describe your experience.")]
        score=round(100*sum(1 for _,ok,_ in checks if ok)/len(checks)) if checks else 0
    return render_template("ats.html",p=p,job=job,jobs=db().execute("SELECT id,title,company FROM jobs ORDER BY title").fetchall(),checks=checks,score=score,has_resume=bool(text))

@app.route("/jobs")
@login_required
def jobs():
    query=request.args.get("q",""); recs=recommendations(profile(),query); saved={r[0] for r in db().execute("SELECT job_id FROM saved_jobs WHERE user_id=?",(session["user_id"],)).fetchall()}
    return render_template("jobs.html",recs=recs,saved=saved,query=query)

@app.post("/jobs/<int:job_id>/save")
@login_required
def save_job(job_id):
    if not db().execute("SELECT 1 FROM jobs WHERE id=?",(job_id,)).fetchone(): abort(404)
    cur=db().execute("DELETE FROM saved_jobs WHERE user_id=? AND job_id=?",(session["user_id"],job_id))
    if not cur.rowcount: db().execute("INSERT INTO saved_jobs(user_id,job_id,created_at) VALUES(?,?,?)",(session["user_id"],job_id,datetime.utcnow().isoformat()))
    db().commit(); return redirect(request.referrer or url_for("jobs"))

@app.route("/jobs/<int:job_id>")
@login_required
def job_detail(job_id):
    job=db().execute("SELECT * FROM jobs WHERE id=?",(job_id,)).fetchone()
    if not job: abort(404)
    score,matched,missing,reasons=score_job(profile(),job)
    return render_template("job_detail.html",job=job,score=score,matched=matched,missing=missing,reasons=reasons,risk=scan_risk(job),saved=bool(db().execute("SELECT 1 FROM saved_jobs WHERE user_id=? AND job_id=?",(session["user_id"],job_id)).fetchone()))

@app.post("/jobs/<int:job_id>/feedback")
@login_required
def job_feedback(job_id):
    if request.form.get("rating") not in ("Relevant","Not relevant"): abort(400)
    db().execute("INSERT INTO feedback(user_id,job_id,rating,created_at) VALUES(?,?,?,?) ON CONFLICT(user_id,job_id) DO UPDATE SET rating=excluded.rating,created_at=excluded.created_at",(session["user_id"],job_id,request.form["rating"],datetime.utcnow().isoformat())); db().commit(); flash("Thanks, your feedback was saved.","success"); return redirect(url_for("job_detail",job_id=job_id))

def scan_risk(job):
    text=(job["description"]+" "+job["title"]+" "+job["company"]+" "+job["apply_url"]).casefold(); flags=[]
    terms=[("pay a fee","Requests for an upfront payment can be a warning sign."),("registration fee","Requests for an upfront payment can be a warning sign."),("guaranteed job","Guaranteed employment claims may be misleading."),("share otp","Never share a one-time password with a recruiter."),("bank password","Never share banking passwords during recruitment."),("urgent hiring","High-pressure urgency can make verification harder.")]
    for term, explanation in terms:
        if term in text and explanation not in flags: flags.append(explanation)
    if not job["apply_url"].startswith("https://"): flags.append("The application link is not HTTPS or is missing; verify the employer through its official site.")
    return flags

@app.route("/skill-gap")
@login_required
def skill_gap():
    recs=recommendations(profile()); target=request.args.get("job",type=int); selected=next((x for x in recs if x["job"]["id"]==target),None) if target else (recs[0] if recs else None)
    return render_template("skill_gap.html",recs=recs,selected=selected,groups=categorize(parse_skills(profile()["technical_skills"]+","+profile()["soft_skills"])),roadmap=roadmap_for(selected["missing"] if selected else []))

def roadmap_for(missing):
    return [{"skill":s,"steps":[f"Learn the core concepts of {s} using a beginner course or documentation.",f"Build a small project that demonstrates {s}.",f"Add evidence and reflect on what you learned about {s}."]} for s in missing]

@app.route("/learning",methods=["GET","POST"])
@login_required
def learning():
    uid=session["user_id"]
    if request.method=="POST":
        action=request.form.get("action")
        if action=="add":
            skill=request.form.get("skill","").strip()
            if skill: db().execute("INSERT INTO learning_items(user_id,skill,priority,resource,created_at) VALUES(?,?,?,?,?)",(uid,skill,request.form.get("priority","Medium"),request.form.get("resource","").strip(),datetime.utcnow().isoformat()))
        elif action=="toggle":
            item=db().execute("SELECT * FROM learning_items WHERE id=? AND user_id=?",(request.form.get("id"),uid)).fetchone()
            if item: db().execute("UPDATE learning_items SET status=? WHERE id=?",("Completed" if item["status"]!="Completed" else "Pending",item["id"]))
        elif action=="delete": db().execute("DELETE FROM learning_items WHERE id=? AND user_id=?",(request.form.get("id"),uid))
        db().commit(); return redirect(url_for("learning"))
    items=db().execute("SELECT * FROM learning_items WHERE user_id=? ORDER BY CASE priority WHEN 'High' THEN 0 WHEN 'Medium' THEN 1 ELSE 2 END,id DESC",(uid,)).fetchall()
    return render_template("learning.html",items=items)

@app.route("/skills",methods=["GET","POST"])
@login_required
def skills_lab():
    uid=session["user_id"]
    challenge_skills=sorted(set(parse_skills(profile()["technical_skills"]+","+profile()["soft_skills"]))) or ["Python","SQL","Communication"]
    if request.method=="POST":
        action=request.form.get("action"); skill=request.form.get("skill","").strip()[:100]
        if action=="challenge":
            answer=request.form.get("answer","").strip()[:4000]
            if answer:
                words=len(re.findall(r"\w+",answer)); has_example=bool(re.search(r"\b(project|example|built|used|created|result|because)\b",answer,re.I)); score=min(100,20+min(words,100)//2+(30 if has_example else 0))
                prompt=request.form.get("prompt",f"Describe how you have used {skill}.")[:500]
                feedback="Good evidence of a practical example. Confirm the details are accurate." if score>=65 else "Add a specific example, explain your own contribution, and describe what you learned."
                db().execute("INSERT INTO challenge_attempts(user_id,skill,prompt,answer,score,feedback,created_at) VALUES(?,?,?,?,?,?,?)",(uid,skill,prompt,answer,score,feedback,datetime.utcnow().isoformat()))
        elif action=="evidence":
            detail=request.form.get("detail","").strip()[:2000]
            if skill and detail: db().execute("INSERT INTO skill_evidence(user_id,skill,evidence_type,detail,url,created_at) VALUES(?,?,?,?,?,?)",(uid,skill,request.form.get("evidence_type","Project")[:40],detail,request.form.get("url","").strip()[:500],datetime.utcnow().isoformat()))
        elif action=="delete_evidence": db().execute("DELETE FROM skill_evidence WHERE id=? AND user_id=?",(request.form.get("id",type=int),uid))
        db().commit(); return redirect(url_for("skills_lab"))
    return render_template("skills_lab.html",challenge_skills=challenge_skills,evidence=db().execute("SELECT * FROM skill_evidence WHERE user_id=? ORDER BY id DESC",(uid,)).fetchall(),attempts=db().execute("SELECT * FROM challenge_attempts WHERE user_id=? ORDER BY id DESC LIMIT 10",(uid,)).fetchall())

@app.route("/alerts",methods=["GET","POST"])
@login_required
def alerts():
    uid=session["user_id"]
    if request.method=="POST":
        action=request.form.get("action")
        if action=="add":
            query=request.form.get("query","").strip()[:120]
            if query: db().execute("INSERT INTO job_alerts(user_id,query,created_at) VALUES(?,?,?)",(uid,query,datetime.utcnow().isoformat()))
        elif action=="toggle": db().execute("UPDATE job_alerts SET active=CASE active WHEN 1 THEN 0 ELSE 1 END WHERE id=? AND user_id=?",(request.form.get("id",type=int),uid))
        elif action=="delete": db().execute("DELETE FROM job_alerts WHERE id=? AND user_id=?",(request.form.get("id",type=int),uid))
        db().commit(); return redirect(url_for("alerts"))
    rows=db().execute("SELECT * FROM job_alerts WHERE user_id=? ORDER BY id DESC",(uid,)).fetchall()
    matches={row["id"]:recommendations(profile(),row["query"])[:5] for row in rows if row["active"]}
    return render_template("alerts.html",alerts=rows,matches=matches)

@app.route("/assistant",methods=["GET","POST"])
@login_required
def assistant():
    answer=""
    if request.method=="POST":
        question=request.form.get("question","").strip().casefold(); p=profile()
        if any(x in question for x in ("skill gap","missing skill","learn")):
            rec=recommendations(p)[:1]; gaps=rec[0]["missing"] if rec else []
            answer=("For your closest listed role, consider exploring: "+", ".join(gaps[:5])+". Add a learning goal and build a small project to show evidence." if gaps else "Add skills and a target role to your profile, then use Skill Gaps to compare against a listing.")
        elif any(x in question for x in ("resume","résumé","cv")):
            answer="Use Resume Studio to review extracted skills and the ATS checker for a basic format checklist. Keep every claim accurate, and create tailored versions in Resume Versions."
        elif any(x in question for x in ("interview","practice")):
            answer="Interview Practice offers prompts and structure feedback. It does not verify technical correctness; use trusted references to check technical answers."
        elif any(x in question for x in ("job","role","search")):
            answer="Explore Jobs lets you search roles and compare requirements. Scores are heuristic estimates from this local sample dataset, not hiring probabilities."
        elif any(x in question for x in ("career","goal","path")):
            answer="Set your target in Career Profile, then open Career Plan for a four-step action plan based on your profile and available listings."
        else: answer="I can help you find jobs, review skill gaps, organize your résumé, plan learning, or practice interviews. Ask about one of those topics. This assistant uses local rules and does not call a generative AI service."
    return render_template("assistant.html",answer=answer)

@app.route("/career")
@login_required
def career():
    p=profile(); goal=p["career_goal"] or p["preferred_roles"] or "your target role"; skills=parse_skills(p["technical_skills"]+","+p["soft_skills"])
    top=recommendations(p)[:1]; missing=top[0]["missing"] if top else []
    paths=[{"stage":"Build foundations","description":"Strengthen role fundamentals and core communication skills.","skills":skills[:4] or ["Choose a target role","Add current skills to your profile"]},{"stage":"Close priority gaps","description":"Focus on high-demand requirements that appear in relevant job listings.","skills":missing[:5] or ["Review job requirements"]},{"stage":"Show evidence","description":"Create a project or portfolio entry that demonstrates your ability.","skills":["Document a real project","Add measurable outcomes only when verified"]},{"stage":"Apply and iterate","description":"Apply to suitable roles, practice interviews and use feedback to adjust your plan.","skills":["Tailor your resume honestly","Track applications"]}]
    return render_template("career.html",p=p,goal=goal,paths=paths,recs=top,roadmap=roadmap_for(missing))

QUESTION_BANK={"python":["What is the difference between a list and a tuple?","How do Python decorators work?","How would you handle exceptions in a file-processing script?"],"sql":["Explain the difference between INNER JOIN and LEFT JOIN.","How would you find duplicate rows in a table?","What is an index and what trade-off does it create?"],"data analytics":["How would you handle missing values in a dataset?","Explain a dashboard insight to a non-technical stakeholder.","How do you validate that a metric is calculated correctly?"],"software testing":["What is the difference between a smoke test and a regression test?","How would you decide what to automate?","Describe a clear bug report."],"hr":["Tell me about yourself and the kind of role you are seeking.","Describe a challenge you worked through.","What do you want to learn in your next role?"]}

@app.route("/interview",methods=["GET","POST"])
@login_required
def interview():
    uid=session["user_id"]; result=None; prompt=""
    if request.method=="POST":
        role=request.form.get("role","").strip() or profile()["preferred_roles"] or "HR"; answer=request.form.get("answer","").strip(); question=request.form.get("question","").strip()
        if request.form.get("action")=="new": prompt=random.choice(QUESTION_BANK.get(role.casefold(),QUESTION_BANK["hr"]))
        elif request.form.get("action")=="prompt": prompt=question
        else:
            words=len(re.findall(r"\w+",answer)); has_example=bool(re.search(r"\b(example|project|result|learned|because|improved)\b",answer,re.I)); score=min(100,20+min(words,100)//2+(25 if has_example else 0)) if words else 0
            feedback="Good start. Add a specific real example and explain your personal contribution." if score<65 else "Clear response structure. Check that each claim reflects your actual experience and add a concise outcome where you can substantiate it."
            cur=db().execute("INSERT INTO interview_sessions(user_id,role,question,answer,feedback,score,created_at) VALUES(?,?,?,?,?,?,?)",(uid,role,question,answer,feedback,score,datetime.utcnow().isoformat())); db().commit(); result={"question":question,"score":score,"feedback":feedback,"id":cur.lastrowid}
    history=db().execute("SELECT * FROM interview_sessions WHERE user_id=? ORDER BY id DESC LIMIT 8",(uid,)).fetchall()
    return render_template("interview.html",result=result,prompt=prompt,history=history,questions=QUESTION_BANK)

@app.route("/cover-letter",methods=["GET","POST"])
@login_required
def cover_letter():
    letter=""
    if request.method=="POST":
        p=profile(); job=db().execute("SELECT * FROM jobs WHERE id=?",(request.form.get("job_id",type=int),)).fetchone() if request.form.get("job_id") else None
        title=request.form.get("title","").strip() or (job["title"] if job else "the role"); company=request.form.get("company","").strip() or (job["company"] if job else "your organization"); evidence=request.form.get("evidence","").strip()
        if not evidence: flash("Add a real project, skill example, or achievement so the draft does not invent experience.","error")
        else:
            letter=f"Dear Hiring Team,\n\nI am applying for the {title} position at {company}. My background in {p['technical_skills'] or p['headline'] or 'the skills listed in my profile'} has encouraged me to pursue this opportunity.\n\nOne relevant example is: {evidence}\n\nI would welcome the opportunity to discuss how my experience and learning goals could contribute to your team. Thank you for your consideration.\n\nSincerely,\n{p['full_name'] or 'Your Name'}"
    return render_template("cover_letter.html",letter=letter,jobs=db().execute("SELECT id,title,company FROM jobs ORDER BY title").fetchall())

@app.route("/applications",methods=["GET","POST"])
@login_required
def applications():
    uid=session["user_id"]
    if request.method=="POST":
        action=request.form.get("action"); appid=request.form.get("id",type=int)
        if action=="add":
            job=db().execute("SELECT * FROM jobs WHERE id=?",(request.form.get("job_id",type=int),)).fetchone() if request.form.get("job_id") else None
            title=request.form.get("title","").strip() or (job["title"] if job else ""); company=request.form.get("company","").strip() or (job["company"] if job else "")
            if title and company: db().execute("INSERT INTO applications(user_id,job_id,title,company,status,applied_date,follow_up,notes,created_at) VALUES(?,?,?,?,?,?,?,?,?)",(uid,job["id"] if job else None,title,company,request.form.get("status","Applied"),request.form.get("applied_date") or None,request.form.get("follow_up") or None,request.form.get("notes","").strip(),datetime.utcnow().isoformat()))
        elif action=="update" and appid: db().execute("UPDATE applications SET status=?,follow_up=?,notes=? WHERE id=? AND user_id=?",(request.form.get("status","Applied"),request.form.get("follow_up") or None,request.form.get("notes","").strip(),appid,uid))
        elif action=="delete" and appid: db().execute("DELETE FROM applications WHERE id=? AND user_id=?",(appid,uid))
        db().commit(); return redirect(url_for("applications"))
    rows=db().execute("SELECT a.*,j.apply_url FROM applications a LEFT JOIN jobs j ON a.job_id=j.id WHERE a.user_id=? ORDER BY a.id DESC",(uid,)).fetchall()
    return render_template("applications.html",apps=rows,jobs=db().execute("SELECT id,title,company FROM jobs ORDER BY title").fetchall(),statuses=["Saved","Applied","Interview","Offer","Rejected"])

@app.route("/saved")
@login_required
def saved():
    rows=db().execute("SELECT j.* FROM saved_jobs s JOIN jobs j ON s.job_id=j.id WHERE s.user_id=? ORDER BY s.created_at DESC",(session["user_id"],)).fetchall(); recs=[]
    for j in rows:
        score,matched,missing,reasons=score_job(profile(),j); recs.append({"job":j,"score":score,"matched":matched,"missing":missing,"reasons":reasons})
    return render_template("saved.html",recs=recs)

@app.route("/market")
@login_required
def market():
    jobs=db().execute("SELECT location,skills,experience_level FROM jobs").fetchall(); skill_counts={}; loc_counts={}
    for j in jobs:
        for s in parse_skills(j["skills"]): skill_counts[s]=skill_counts.get(s,0)+1
        loc_counts[j["location"]]=loc_counts.get(j["location"],0)+1
    return render_template("market.html",skills=sorted(skill_counts.items(),key=lambda x:x[1],reverse=True)[:12],locations=sorted(loc_counts.items(),key=lambda x:x[1],reverse=True),total=len(jobs))

@app.route("/admin")
@admin_required
def admin():
    stats={"users":db().execute("SELECT COUNT(*) FROM users WHERE role='user'").fetchone()[0],"jobs":db().execute("SELECT COUNT(*) FROM jobs").fetchone()[0],"apps":db().execute("SELECT COUNT(*) FROM applications").fetchone()[0],"feedback":db().execute("SELECT COUNT(*) FROM feedback").fetchone()[0],"reports":db().execute("SELECT COUNT(*) FROM reports").fetchone()[0]}
    feedback=db().execute("SELECT rating,COUNT(*) count FROM feedback GROUP BY rating").fetchall()
    return render_template("admin.html",stats=stats,feedback=feedback,categories=db().execute("SELECT * FROM job_categories ORDER BY name").fetchall(),jobs=db().execute("SELECT * FROM jobs ORDER BY id DESC").fetchall(),users=db().execute("SELECT id,email,created_at FROM users WHERE role='user' ORDER BY id DESC LIMIT 30").fetchall(),reports=db().execute("SELECT r.*,u.email,j.title FROM reports r JOIN users u ON u.id=r.user_id LEFT JOIN jobs j ON j.id=r.job_id ORDER BY r.id DESC LIMIT 20").fetchall())

@app.route("/admin/data")
@admin_required
def admin_data():
    counts=db().execute("SELECT rating,COUNT(*) count FROM feedback GROUP BY rating").fetchall()
    return render_template("admin_data.html",categories=db().execute("SELECT * FROM job_categories ORDER BY name").fetchall(),feedback=counts,job_count=db().execute("SELECT COUNT(*) FROM jobs").fetchone()[0])

@app.post("/admin/import-jobs")
@admin_required
def admin_import_jobs():
    uploaded=request.files.get("csv_file")
    if not uploaded or not uploaded.filename.lower().endswith(".csv"):
        flash("Choose a CSV file.","error"); return redirect(url_for("admin"))
    try:
        rows=csv.DictReader(io.StringIO(uploaded.stream.read().decode("utf-8-sig")))
        added=0
        for row in rows:
            normalized={str(k).strip().casefold():str(v or "").strip() for k,v in row.items() if k}
            title=normalized.get("title",""); company=normalized.get("company","")
            if not title or not company: continue
            db().execute("INSERT INTO jobs(title,company,location,employment_type,experience_level,qualification,description,skills,apply_url,salary,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(title[:160],company[:160],normalized.get("location","")[:160],normalized.get("employment_type","Full-time")[:60],normalized.get("experience_level","Entry-level")[:60],normalized.get("qualification","")[:500],normalized.get("description","")[:5000],", ".join(parse_skills(normalized.get("skills","")))[:1000],normalized.get("apply_url","")[:1000],normalized.get("salary","")[:100],datetime.utcnow().isoformat()))
            added+=1
        db().commit(); flash(f"Imported {added} job rows. Rows without title and company were skipped.","success")
    except (UnicodeDecodeError,csv.Error) as exc: db().rollback(); flash("Could not parse the CSV. Save it as UTF-8 CSV and try again.","error")
    return redirect(url_for("admin"))

@app.post("/admin/categories")
@admin_required
def admin_categories():
    action=request.form.get("action"); name=request.form.get("name","").strip()[:100]
    if action=="delete": db().execute("DELETE FROM job_categories WHERE id=?",(request.form.get("id",type=int),))
    elif name:
        try: db().execute("INSERT INTO job_categories(name,description) VALUES(?,?)",(name,request.form.get("description","").strip()[:300]))
        except sqlite3.IntegrityError: flash("That category already exists.","info")
    db().commit(); return redirect(url_for("admin"))

@app.route("/admin/jobs",methods=["POST"])
@admin_required
def admin_jobs():
    if request.form.get("action")=="delete": db().execute("DELETE FROM jobs WHERE id=?",(request.form.get("id",type=int),))
    else:
        title=request.form.get("title","").strip(); company=request.form.get("company","").strip()
        if title and company: db().execute("INSERT INTO jobs(title,company,location,employment_type,experience_level,qualification,description,skills,apply_url,salary,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(title,company,request.form.get("location",""),request.form.get("employment_type","Full-time"),request.form.get("experience_level","Entry-level"),request.form.get("qualification",""),request.form.get("description",""),", ".join(parse_skills(request.form.get("skills",""))),request.form.get("apply_url",""),request.form.get("salary",""),datetime.utcnow().isoformat()))
    db().commit(); flash("Job data updated.","success"); return redirect(url_for("admin"))

@app.post("/jobs/<int:job_id>/report")
@login_required
def report_job(job_id):
    reason=request.form.get("reason","").strip()
    if not db().execute("SELECT 1 FROM jobs WHERE id=?",(job_id,)).fetchone(): abort(404)
    if reason: db().execute("INSERT INTO reports(user_id,job_id,reason,created_at) VALUES(?,?,?,?)",(session["user_id"],job_id,reason[:500],datetime.utcnow().isoformat())); db().commit(); flash("Report sent for admin review.","success")
    return redirect(url_for("job_detail",job_id=job_id))

@app.post("/account/delete")
@login_required
def delete_account():
    uid=session["user_id"]; p=profile(); filename=p.get("resume_filename");
    if filename: (UPLOAD_DIR/secure_filename(filename)).unlink(missing_ok=True)
    db().execute("DELETE FROM users WHERE id=?",(uid,)); db().commit(); session.clear(); flash("Your account and associated profile data were deleted.","success"); return redirect(url_for("index"))

@app.errorhandler(413)
def too_large(_e): return render_template("error.html",code=413,message="Upload is too large. Maximum PDF size is 8 MB."),413

@app.errorhandler(403)
def forbidden(_e): return render_template("error.html",code=403,message="You do not have access to this page."),403

init_db()

if __name__=="__main__": app.run(debug=os.environ.get("FLASK_DEBUG")=="1",host="127.0.0.1",port=int(os.environ.get("PORT",5000)))
