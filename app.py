"""
WhereGradsGo — find jobs where your university's graduates actually work.

Run locally:   streamlit run app.py
Needs:         pip install streamlit requests pypdf
Data file:     employers.json  (must sit next to this file)
"""

import json
import requests
import streamlit as st

# resume parsing is optional — app still runs if these aren't installed
try:
    from pypdf import PdfReader
    PYPDF_OK = True
except Exception:
    PYPDF_OK = False

try:
    from google import genai
    GENAI_OK = True
except Exception:
    GENAI_OK = False


# ── RESUME ENGINE (Gemini-powered) ────────────────────────────────────────────
# Instead of a fixed keyword list, we send the resume text to Google's Gemini
# model, which UNDERSTANDS the person's actual skills/interests (not just their
# degree) and maps them to job categories. Robust to any skill, any field.

# Adzuna's real category labels — Gemini maps to these exact strings so the
# result plugs straight into the job filter.
ADZUNA_CATEGORIES = [
    "IT Jobs", "Healthcare & Nursing Jobs", "Engineering Jobs",
    "Accounting & Finance Jobs", "Teaching Jobs", "Admin Jobs",
    "Trade & Construction Jobs", "Hospitality & Catering Jobs",
    "PR, Advertising & Marketing Jobs", "Sales Jobs", "Customer Services Jobs",
    "Logistics & Warehouse Jobs", "Retail Jobs", "Creative & Design Jobs",
    "Legal Jobs", "Scientific & QA Jobs", "Social work Jobs", "Property Jobs",
    "Manufacturing Jobs", "Energy, Oil & Gas Jobs", "Charity & Voluntary Jobs",
    "HR & Recruitment Jobs", "Other/General Jobs",
]

def _build_prompt(resume_text):
    cats = "\n".join(f"- {c}" for c in ADZUNA_CATEGORIES)
    return f"""You are a career advisor. Read this resume and identify the person's \
actual skills and interests, then choose which job categories best fit them.

IMPORTANT RULES:
- Judge by their ACTUAL skills, projects, and interests — NOT just their degree.
- A person studying one field may have skills or passion in another. Respect that.
- Pick 1 to 4 categories, ordered best-fit first.
- Choose ONLY from this exact list (copy the strings exactly):
{cats}

Return ONLY valid JSON, no other text:
{{"categories": ["Exact Category 1", "Exact Category 2"], "summary": "one short sentence on their strengths"}}

RESUME:
{resume_text}
"""

def analyse_resume(uploaded_file, api_key):
    """Read a PDF resume, ask Gemini to understand it, return matched categories."""
    # 1. extract text from the PDF
    if not PYPDF_OK:
        return {"ok": False, "error": "pypdf not installed"}
    try:
        reader = PdfReader(uploaded_file)
        text = "\n".join((p.extract_text() or "") for p in reader.pages)
    except Exception:
        return {"ok": False, "error": "Couldn't read that PDF."}
    if len(text.strip()) < 30:
        return {"ok": False, "error": "No readable text found (scanned image?)."}

    # 2. ask Gemini to understand it (with retries for transient 503/429)
    if not GENAI_OK:
        return {"ok": False, "error": "google-genai not installed"}
    import time
    last_err = ""
    for attempt in range(4):
        try:
            client = genai.Client(api_key=api_key)
            resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=_build_prompt(text[:8000]),
            )
            raw = (resp.text or "").replace("```json", "").replace("```", "").strip()
            data = json.loads(raw)
            cats = [c for c in data.get("categories", []) if c in ADZUNA_CATEGORIES]
            return {"ok": True, "categories": cats, "summary": data.get("summary", "")}
        except Exception as e:
            last_err = str(e)
            # transient errors → wait and retry; otherwise stop
            if "503" in last_err or "429" in last_err or "UNAVAILABLE" in last_err:
                time.sleep(2 * (attempt + 1))  # 2s, 4s, 6s
                continue
            return {"ok": False, "error": f"AI analysis failed: {last_err[:120]}"}
    return {"ok": False, "error": "AI is busy right now — please try again in a moment."}

# ── API CREDENTIALS ───────────────────────────────────────────────────────────
def get_secret(key, default):
    try:
        return st.secrets[key]
    except Exception:
        return default

APP_ID = get_secret("ADZUNA_APP_ID", "")
APP_KEY = get_secret("ADZUNA_APP_KEY", "")
GEMINI_KEY = get_secret("GEMINI_API_KEY", "")
ADZUNA_URL = "https://api.adzuna.com/v1/api/jobs/au/search/1"
KOFI_URL = "https://ko-fi.com/harshrastogi"

# Adzuna keys are required for the core job search.
def _keys_missing():
    return not APP_ID or not APP_KEY


# ── COURSE CATALOG ────────────────────────────────────────────────────────────
# Keyed to Adzuna's exact category strings so it plugs straight into resume
# matches and the interest filter. Plain links for now — swap to affiliate links
# once programs approve. Free options are genuinely free; we earn nothing.
COURSE_CATALOG = {
    "IT Jobs": {
        "free": [("freeCodeCamp — full coding & data curriculum", "https://www.freecodecamp.org/learn"),
                 ("Kaggle Learn — hands-on data science", "https://www.kaggle.com/learn")],
        "paid": [("Google Data Analytics Certificate (Coursera)", "https://www.coursera.org/professional-certificates/google-data-analytics"),
                 ("Python courses (Udemy)", "https://www.udemy.com/topic/python/")],
    },
    "PR, Advertising & Marketing Jobs": {
        "free": [("HubSpot Academy — free marketing certs", "https://academy.hubspot.com/courses"),
                 ("Google Skillshop — Ads & Analytics", "https://skillshop.withgoogle.com/")],
        "paid": [("Google Digital Marketing Certificate (Coursera)", "https://www.coursera.org/professional-certificates/google-digital-marketing-ecommerce"),
                 ("Digital marketing courses (Udemy)", "https://www.udemy.com/topic/digital-marketing/")],
    },
    "Accounting & Finance Jobs": {
        "free": [("Khan Academy — finance & economics", "https://www.khanacademy.org/economics-finance-domain"),
                 ("Xero training (widely used in AU)", "https://www.xero.com/au/training/")],
        "paid": [("Finance courses (Coursera)", "https://www.coursera.org/browse/business/finance"),
                 ("Accounting courses (Udemy)", "https://www.udemy.com/topic/accounting/")],
    },
    "Admin Jobs": {
        "free": [("Microsoft Learn — Office & productivity", "https://learn.microsoft.com/training/")],
        "paid": [("Excel courses (Udemy)", "https://www.udemy.com/topic/excel/")],
    },
    "Engineering Jobs": {
        "free": [("MIT OpenCourseWare — engineering", "https://ocw.mit.edu/")],
        "paid": [("AutoCAD courses (Udemy)", "https://www.udemy.com/topic/autocad/")],
    },
    "Healthcare & Nursing Jobs": {
        "free": [("FutureLearn — healthcare courses", "https://www.futurelearn.com/subjects/healthcare-medicine-courses")],
        "paid": [("Health courses (Coursera)", "https://www.coursera.org/browse/health")],
    },
    "Teaching Jobs": {
        "free": [("FutureLearn — teaching courses", "https://www.futurelearn.com/subjects/teaching-courses")],
        "paid": [("Education courses (Coursera)", "https://www.coursera.org/browse/social-sciences/education")],
    },
    "Sales Jobs": {
        "free": [("HubSpot Academy — free sales training", "https://academy.hubspot.com/courses?topic=sales")],
        "paid": [("Sales courses (Udemy)", "https://www.udemy.com/topic/sales-skills/")],
    },
    "Customer Services Jobs": {
        "free": [("HubSpot Academy — service training", "https://academy.hubspot.com/courses?topic=service")],
        "paid": [("Customer service courses (Udemy)", "https://www.udemy.com/topic/customer-service/")],
    },
    "Creative & Design Jobs": {
        "free": [("Canva Design School", "https://www.canva.com/designschool/")],
        "paid": [("Design courses (Skillshare)", "https://www.skillshare.com/en/browse/design")],
    },
}

# Tabler-style emoji icon per category (kept simple — no external font needed).
CATEGORY_ICONS = {
    "IT Jobs": "💻",
    "PR, Advertising & Marketing Jobs": "📣",
    "Accounting & Finance Jobs": "🧮",
    "Admin Jobs": "🗂️",
    "Engineering Jobs": "🛠️",
    "Healthcare & Nursing Jobs": "🩺",
    "Teaching Jobs": "🏫",
    "Sales Jobs": "📈",
    "Customer Services Jobs": "🎧",
    "Creative & Design Jobs": "🎨",
}


def render_growth_panel(matched_cats, max_cards=3):
    """Render a 'Grow your skills' panel for the matched categories.

    matched_cats: ordered list of Adzuna category strings (resume match first,
    else the user's chosen interest filters). Only categories we have curated
    learning options for are shown, capped at max_cards.
    """
    shown = [c for c in matched_cats if c in COURSE_CATALOG][:max_cards]
    if not shown:
        return

    def _row(label, url, is_free):
        tag = "Free" if is_free else "Paid"
        tag_cls = "tag-free" if is_free else "tag-paid"
        return (
            f'<a class="course-row" href="{url}" target="_blank" rel="noopener">'
            f'<span class="course-label"><span class="course-tag {tag_cls}">{tag}</span>'
            f'{label}</span><span class="course-ext">↗</span></a>'
        )

    cards = []
    for cat in shown:
        opts = COURSE_CATALOG[cat]
        icon = CATEGORY_ICONS.get(cat, "🌱")
        rows = "".join(_row(l, u, True) for l, u in opts.get("free", []))
        rows += "".join(_row(l, u, False) for l, u in opts.get("paid", []))
        # tidy the display name (drop trailing " Jobs")
        nice = cat[:-5] if cat.endswith(" Jobs") else cat
        cards.append(
            f'<div class="grow-card"><div class="grow-card-head">'
            f'<span class="grow-card-icon">{icon}</span>'
            f'<span class="grow-card-title">{nice}</span></div>'
            f'<div class="grow-rows">{rows}</div></div>'
        )

    st.markdown(f"""
<div class="grow-panel">
  <div class="grow-head">
    <span class="grow-seed">🌱</span>
    <span class="grow-title">Grow your skills</span>
  </div>
  <div class="grow-sub">Free options are genuinely free. Paid courses include a
    shareable certificate, which helps prove the skill to employers — pick whatever
    fits your budget. These are plain links; we earn nothing from them.</div>
  <div class="grow-grid">{''.join(cards)}</div>
  <div class="grow-support">WhereGradsGo is free and earns nothing from these links.
    If it helped you, you can <a href="{KOFI_URL}" target="_blank" rel="noopener">buy me a coffee on Ko-fi ☕</a></div>
</div>
""", unsafe_allow_html=True)


# ── DATA ────────────────────────────────────────────────────────────────────--
@st.cache_data
def load_universities():
    with open("employers.json") as f:
        return json.load(f)["universities"]


@st.cache_data(ttl=3600)
def fetch_jobs(employer_name, region, max_results=30):
    params = {
        "app_id": APP_ID, "app_key": APP_KEY,
        "results_per_page": max_results, "what": employer_name, "where": region,
    }
    try:
        r = requests.get(ADZUNA_URL, params=params, timeout=30)
        r.raise_for_status()
        raw = r.json().get("results", [])
    except Exception as e:
        st.error(f"Couldn't fetch jobs for {employer_name}: {e}")
        return []
    jobs = []
    for j in raw:
        jobs.append({
            "title": j.get("title", ""),
            "employer": j.get("company", {}).get("display_name", ""),
            "category": j.get("category", {}).get("label", "Other/General Jobs"),
            "location": j.get("location", {}).get("display_name", ""),
            "contract": (j.get("contract_time") or "n/a").replace("_", "-"),
            "created": j.get("created", "")[:10],
            "url": j.get("redirect_url", ""),
            "matched_employer": employer_name,
        })
    return jobs


# ── PAGE CONFIG ─────────────────────────────────────────────────────────────--
st.set_page_config(page_title="WhereGradsGo", page_icon="🎓",
                   layout="centered", initial_sidebar_state="collapsed")

# ── CUSTOM STYLING ────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Libre+Franklin:wght@400;500;600;700;800&family=Newsreader:opsz,wght@6..72,400;6..72,500;6..72,600&display=swap');

:root {
  --ink: #1d1d1f;
  --paper: #f6f3ee;
  --card: #ffffff;
  --accent: #b3431a;
  --accent-soft: #f7e7df;
  --line: #e4ddd2;
  --muted: #6b6358;
}

.stApp { background: var(--paper); }
/* Scale the whole app down. Streamlit overrides root html, so target stApp too. */
html { font-size: 88%; }
.stApp, [data-testid="stAppViewContainer"] { font-size: 14px; }
.block-container { max-width: 1050px; padding-top: 2rem; }
html, body, [class*="css"], .stMarkdown, p, span, div, label {
  font-family: 'Libre Franklin', -apple-system, sans-serif;
  color: var(--ink);
}

/* ---- MASTHEAD (newspaper-style hero) ---- */
.masthead { text-align: center; padding: 4px 0 0; margin-bottom: 6px; }
.masthead .dateline {
  display: flex; justify-content: center; flex-wrap: wrap; gap: 6px 14px;
  font-size: 10.5px; letter-spacing: 0.18em; text-transform: uppercase;
  color: var(--muted); font-weight: 600;
  border-top: 1px solid var(--ink); border-bottom: 1px solid var(--line);
  padding: 7px 0; margin-bottom: 22px;
}
.masthead .dateline .dl-dot { color: var(--accent); }
.masthead h1 {
  font-family: 'Newsreader', Georgia, serif; font-weight: 500; font-size: 58px;
  line-height: 1.0; letter-spacing: -0.025em; margin: 0; color: var(--ink);
}
.masthead h1 .go { color: var(--accent); font-style: italic; }
.masthead .sub {
  font-family: 'Newsreader', Georgia, serif; font-style: italic;
  font-size: 16px; color: var(--muted); margin-top: 10px; font-weight: 400;
}
.masthead .rule-thick { height: 3px; background: var(--ink); margin-top: 20px; }
.masthead .rule-thin { height: 1px; background: var(--ink); margin-top: 3px; }
.masthead .howline {
  font-size: 11px; letter-spacing: 0.14em; text-transform: uppercase;
  color: var(--muted); font-weight: 600; padding: 9px 0 0;
}
.masthead .howline .step-n {
  font-family: 'Newsreader', serif; font-style: italic; font-weight: 600;
  color: var(--accent); text-transform: none; letter-spacing: 0; font-size: 13px;
}

/* ---- UNIVERSITY BANNER ---- */
.uni-banner {
  background: linear-gradient(135deg, #1d1d1f 0%, #2b2118 100%);
  border-radius: 16px; border-bottom: 3px solid var(--accent);
  padding: 22px 26px; margin: 16px 0 6px;
  display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;
}
.uni-banner .uni-name {
  font-family: 'Newsreader', serif; font-size: 24px; font-weight: 600; color: #ffffff;
}
.uni-banner .uni-loc { color: #b8b0a4; font-size: 13.5px; margin-top: 3px; }
.qs-badge {
  background: var(--accent); color: #fff; border-radius: 10px;
  padding: 8px 16px; text-align: center; white-space: nowrap;
}
.qs-badge .label { font-size: 9.5px; text-transform: uppercase; letter-spacing: 0.13em; opacity: 0.9; display:block; color:#fff; }
.qs-badge .num { font-size: 19px; font-weight: 700; color:#fff; }

/* ---- JOB CARD ---- */
.job-card {
  background: var(--card); border: 1px solid var(--line); border-radius: 12px;
  border-left: 3px solid var(--line);
  padding: 18px 20px; margin-bottom: 12px; transition: all .16s ease;
}
.job-card:hover { border-color: var(--line); border-left-color: var(--accent);
  transform: translateY(-2px); box-shadow: 0 10px 28px rgba(29,29,31,.09); }
.job-title { font-family: 'Newsreader', serif; font-size: 20px; font-weight: 600;
  line-height: 1.25; margin: 0 0 3px; color: var(--ink); }
.job-employer { font-weight: 600; font-size: 13.5px; color: var(--accent); margin-bottom: 9px; }
.job-meta { font-size: 12.5px; color: var(--muted); }
.cat-pill {
  display: inline-block; background: var(--accent-soft); color: var(--accent);
  border-radius: 5px; padding: 2px 8px; font-size: 11.5px; font-weight: 600; margin-right: 6px;
}

/* ---- SECTION LABELS ---- */
.section-label {
  display: flex; align-items: center; gap: 12px;
  font-size: 11px; text-transform: uppercase; letter-spacing: 0.15em;
  color: var(--muted); font-weight: 700; margin: 16px 0 6px;
}
.section-label::after { content: ""; flex: 1; height: 1px; background: var(--line); }
.count-big { font-family: 'Newsreader', serif; font-size: 32px; font-weight: 600; color: var(--ink); }

/* ---- LINK BUTTON ---- */
.stLinkButton a {
  background: var(--ink) !important; color: #ffffff !important;
  border: none !important; border-radius: 999px !important; font-weight: 600 !important;
}
.stLinkButton a:hover { background: var(--accent) !important; color:#fff !important; }
.stLinkButton a p { color:#ffffff !important; }

/* ---- SIDEBAR: force dark, readable text on light bg ---- */
[data-testid="stSidebar"] { background: #ebe5db; border-right: 1.5px solid var(--ink); }
[data-testid="stSidebar"] * { color: var(--ink) !important; }
[data-testid="stSidebar"] .stCaption, [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
  color: var(--muted) !important;
}
[data-testid="stSidebar"] h3 { color: var(--ink) !important; font-weight: 700; }

footer, #MainMenu { visibility: hidden; }

/* ---- DROPDOWN POPUP MENUS: readable text ---- */
/* the popover list that appears when a selectbox/multiselect is opened */
[data-baseweb="popover"] { background: #ffffff !important; }
[data-baseweb="popover"] li,
[data-baseweb="popover"] [role="option"],
[data-baseweb="menu"] li,
ul[role="listbox"] li {
  color: var(--ink) !important;
  background: #ffffff !important;
}
[data-baseweb="popover"] li:hover,
[data-baseweb="popover"] [role="option"]:hover,
ul[role="listbox"] li:hover {
  background: var(--accent-soft) !important;
  color: var(--accent) !important;
}
/* selected-value text inside the closed select boxes */
[data-baseweb="select"] div { color: var(--ink) !important; }
/* multiselect chosen tags */
[data-baseweb="tag"] { background: var(--accent) !important; }
[data-baseweb="tag"] span { color: #ffffff !important; }

/* ---- FIX: closed select boxes — white bg, dark text (was dark-on-dark) ---- */
[data-baseweb="select"] > div {
  background: #ffffff !important;
  border: 1px solid var(--line) !important;
}
[data-baseweb="select"] > div > div,
[data-baseweb="select"] [data-baseweb="input"] div,
[data-baseweb="select"] span {
  color: var(--ink) !important;
  -webkit-text-fill-color: var(--ink) !important;
}
/* the placeholder / single selected value text */
[data-baseweb="select"] div[value], 
[data-baseweb="select"] div[aria-selected] { color: var(--ink) !important; }

/* ---- FIX: hide Streamlit's dark top header bar ---- */
[data-testid="stHeader"] { display: none !important; }
[data-testid="stToolbar"] { display: none !important; }
.stApp > header { display: none !important; }
[data-testid="stAppViewContainer"] > .main { padding-top: 0 !important; }

/* ---- FIX: dropdown option HOVER/HIGHLIGHT state (was dark box, dark text) ---- */
ul[role="listbox"] li[aria-selected="true"],
ul[role="listbox"] li:hover,
[data-baseweb="menu"] li[aria-selected="true"],
[data-baseweb="menu"] li:hover,
[role="option"][aria-selected="true"],
[role="option"]:hover {
  background-color: var(--accent-soft) !important;
  color: var(--accent) !important;
}
/* make sure ALL text inside a hovered/highlighted option is readable */
ul[role="listbox"] li:hover *,
ul[role="listbox"] li[aria-selected="true"] *,
[role="option"]:hover *,
[role="option"][aria-selected="true"] * {
  color: var(--accent) !important;
  -webkit-text-fill-color: var(--accent) !important;
  background-color: transparent !important;
}

/* ---- FIX: file uploader drop-zone + expander panels (dark by default) ---- */
[data-testid="stFileUploader"] section,
[data-testid="stFileUploaderDropzone"] {
  background: #ffffff !important; border: 1.5px dashed var(--line) !important;
}
[data-testid="stFileUploader"] section *,
[data-testid="stFileUploaderDropzone"] * { color: var(--ink) !important; }
[data-testid="stFileUploader"] button {
  background: var(--ink) !important; color: #fff !important; border: none !important;
}
[data-testid="stFileUploader"] button * { color:#fff !important; }
/* uploaded-file chip */
[data-testid="stFileUploaderFile"] { background:#ffffff !important; }
[data-testid="stFileUploaderFile"] * { color: var(--ink) !important; }
/* expander ("What we detected") */
[data-testid="stExpander"] details,
[data-testid="stExpander"] summary {
  background: #ffffff !important; color: var(--ink) !important;
  border: 1px solid var(--line) !important; border-radius: 8px !important;
}
[data-testid="stExpander"] * { color: var(--ink) !important; }

/* ---- No sidebar: controls are in the main page now (mobile-safe) ---- */
[data-testid="stSidebar"] { display: none !important; }
[data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"] { display: none !important; }

/* ---- GROW YOUR SKILLS PANEL ---- */
.grow-panel {
  background: var(--card); border: 1px solid var(--line); border-radius: 14px;
  padding: 20px 22px; margin: 8px 0 4px;
}
.grow-head { display: flex; align-items: center; gap: 9px; margin-bottom: 6px; }
.grow-seed { font-size: 20px; line-height: 1; }
.grow-title {
  font-family: 'Newsreader', serif; font-size: 22px; font-weight: 600; color: var(--ink);
}
.grow-sub { font-size: 12.5px; color: var(--muted); line-height: 1.55; margin-bottom: 16px; }
.grow-grid {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 12px;
}
.grow-card {
  background: var(--paper); border: 1px solid var(--line); border-radius: 12px; padding: 14px 16px;
}
.grow-card-head { display: flex; align-items: center; gap: 8px; margin-bottom: 11px; }
.grow-card-icon { font-size: 17px; line-height: 1; }
.grow-card-title { font-weight: 700; font-size: 14px; color: var(--ink); }
.grow-rows { display: flex; flex-direction: column; gap: 7px; }
.course-row {
  display: flex; align-items: center; justify-content: space-between; gap: 8px;
  background: var(--card); border: 1px solid var(--line); border-radius: 8px;
  padding: 8px 11px; text-decoration: none !important; transition: all .14s ease;
}
.course-row:hover { border-color: var(--accent); transform: translateY(-1px); }
.course-label {
  display: flex; align-items: center; gap: 8px;
  font-size: 12.5px; color: var(--ink) !important; line-height: 1.35;
}
.course-tag {
  flex-shrink: 0; font-size: 10px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.04em; padding: 2px 8px; border-radius: 5px;
}
.tag-free { background: #e3f0e4; color: #2f6b34; }
.tag-paid { background: var(--accent-soft); color: var(--accent); }
.course-ext { flex-shrink: 0; color: var(--muted); font-size: 13px; }

/* ---- KO-FI + SUPPORT ---- */
.kofi-btn {
  display: inline-flex; align-items: center; gap: 7px; white-space: nowrap;
  background: var(--ink); color: #ffffff !important; text-decoration: none !important;
  border-radius: 999px; padding: 8px 18px; font-size: 13px; font-weight: 600;
  transition: all .16s ease;
}
.kofi-btn:hover { background: var(--accent); transform: translateY(-1px); }
.grow-support { font-size: 12px; color: var(--muted); margin-top: 14px;
  padding-top: 12px; border-top: 1px dashed var(--line); }
.grow-support a { color: var(--accent) !important; font-weight: 600; text-decoration: none; }
.grow-support a:hover { text-decoration: underline; }

/* ---- SITE FOOTER (editorial colophon) ---- */
.site-footer { margin-top: 28px; }
.site-footer .rule-thin { height: 1px; background: var(--ink); }
.site-footer .rule-thick { height: 3px; background: var(--ink); margin-top: 3px; }
.site-footer .footer-row {
  display: flex; justify-content: space-between; align-items: center;
  flex-wrap: wrap; gap: 14px; padding: 18px 0 6px;
}
.site-footer .footer-credits { font-size: 12px; color: var(--muted); line-height: 1.6; max-width: 620px; }
.site-footer .footer-note {
  font-family: 'Newsreader', serif; font-style: italic;
  font-size: 12.5px; color: var(--muted); padding: 4px 0 14px;
}

/* ---- ACCESSIBILITY: respect reduced motion ---- */
@media (prefers-reduced-motion: reduce) {
  * { transition: none !important; }
  .job-card:hover, .course-row:hover, .kofi-btn:hover { transform: none !important; }
}

/* ---- MOBILE sizing tweaks ---- */
@media (max-width: 768px) {
  .masthead h1 { font-size: 36px !important; }
  .masthead .sub { font-size: 14px !important; }
  .masthead .dateline { font-size: 9.5px !important; gap: 4px 10px !important; }
  .masthead .howline { font-size: 10px !important; }
  .block-container { padding: 1rem 0.6rem !important; max-width: 100% !important; }
  .uni-banner { padding: 16px 18px !important; }
  .uni-banner .uni-name { font-size: 20px !important; }
  .job-title { font-size: 17px !important; }
  .site-footer .footer-row { flex-direction: column; align-items: flex-start; }
}
</style>
""", unsafe_allow_html=True)


# ── LOAD DATA ───────────────────────────────────────────────────────────────--
universities = load_universities()

def uni_label(u):
    qs = f"QS #{u['qs']}" if u.get("qs") else "Unranked"
    mark = "✅ " if u.get("mode") == "alumni" else ""
    return f"{mark}{u['name']} · {u['city']} · {qs}"

# sort: curated-alumni universities first (CDU leading), then others by QS rank
def sort_key(u):
    is_alumni = u.get("mode") == "alumni"
    if u["id"] == "cdu":
        return (0, 0)
    if is_alumni:
        return (0, u["qs"] if u.get("qs") else 9999)
    return (1, u["qs"] if u.get("qs") else 9999)
universities_sorted = sorted(universities, key=sort_key)


# ── MASTHEAD ──────────────────────────────────────────────────────────────────
n_unis = len(universities_sorted)
n_emps = sum(len(u.get("employers", [])) for u in universities_sorted)
st.markdown(f"""
<div class="masthead">
  <div class="dateline">
    <span>Australia</span><span class="dl-dot">●</span>
    <span>{n_unis} universities</span><span class="dl-dot">●</span>
    <span>{n_emps} employers</span><span class="dl-dot">●</span>
    <span>Live listings via Adzuna</span>
  </div>
  <h1>WhereGrads<span class="go">Go</span></h1>
  <div class="sub">Find live jobs at the organisations your university's graduates actually work for.</div>
  <div class="rule-thick"></div>
  <div class="rule-thin"></div>
  <div class="howline">
    <span class="step-n">i.</span> Pick your university &nbsp;
    <span class="step-n">ii.</span> See where its grads work &nbsp;
    <span class="step-n">iii.</span> Apply to live openings
  </div>
</div>
""", unsafe_allow_html=True)

# If the core API keys aren't configured, show setup help and stop.
if _keys_missing():
    st.warning(
        "**Setup needed.** This app needs Adzuna API keys to fetch jobs.\n\n"
        "Locally: create `.streamlit/secrets.toml` with your keys "
        "(see `secrets.toml.example`).\n\n"
        "Deployed: add them in your app's **Settings → Secrets**."
    )
    st.stop()


# ── ABOUT ─────────────────────────────────────────────────────────────────────
with st.expander("About WhereGradsGo — how it works & data honesty"):
    st.markdown("""
**The idea:** Employers that hire a lot of a university's graduates tend to keep
hiring them. WhereGradsGo helps students start their search from those organisations,
then shows live job openings there.

**How job matching works:**
- Pick your university → see its key employers.
- Browse live jobs at those employers (pulled from the Adzuna job API).
- Filter by area of interest, or upload your resume and let AI match jobs to your
  actual skills.
- "Apply" takes you to the original job posting.

**Being honest about the data:**
- **✅ Curated universities** (Charles Darwin, Tasmania, James Cook, Charles Sturt,
  University of New England, CQUniversity, Federation): these show employer lists
  compiled from public, regional employment sources — a genuine reflection of where
  graduates commonly work.
- **Other universities:** these show the *largest graduate employers in the state*,
  which is a useful starting point but **not** a verified alumni list for that
  specific university. We label this clearly so you know what you're seeing.
- We do **not** scrape LinkedIn or any site's private data. Job listings come from a
  proper job API; employer lists are curated from public information.
- **Resume privacy:** if you upload a resume, its text is sent to Google's Gemini
  (free tier) to identify your skills. Don't upload anything you're not comfortable
  sharing with a third-party AI service.

*QS rankings from QS World University Rankings 2026.*
""")


# ── CONTROLS (main page — always visible, mobile-safe) ───────────────────────--
st.markdown('<div class="section-label">🎓 Find your university</div>', unsafe_allow_html=True)
c1, c2 = st.columns([1, 1])
with c1:
    labels = [uni_label(u) for u in universities_sorted]
    idx = st.selectbox("University", range(len(labels)),
                       format_func=lambda i: labels[i], label_visibility="collapsed")
    uni = universities_sorted[idx]

mode = uni.get("mode", "")
has_employers = len(uni["employers"]) > 0
with c2:
    if has_employers:
        emp_label = "Employer" if mode == "alumni" else "Major employer"
        employer_options = ["All employers"] + [e["name"] for e in uni["employers"]]
        chosen_employer = st.selectbox(emp_label, employer_options, label_visibility="collapsed")
    else:
        chosen_employer = None
        st.write("")

# ── Resume upload (AI-powered) ──
resume_cats = []
with st.expander("📄 Smart match — upload your resume to match jobs to your skills"):
    if PYPDF_OK and GENAI_OK and GEMINI_KEY:
        resume_file = st.file_uploader(
            "Upload your resume (PDF). AI reads your skills and matches jobs.",
            type=["pdf"])
        if resume_file is not None:
            with st.spinner("AI is reading your resume..."):
                result = analyse_resume(resume_file, GEMINI_KEY)
            if result["ok"] and result["categories"]:
                resume_cats = result["categories"]
                top = resume_cats[0]
                st.success(f"Best match → **{top}**"
                           + (f" +{len(resume_cats)-1} more" if len(resume_cats) > 1 else ""))
                if result.get("summary"):
                    st.caption(f"💡 {result['summary']}")
                st.markdown("**All matched areas:** " + " · ".join(resume_cats))
            elif result["ok"]:
                st.warning("AI couldn't confidently match your resume. "
                           "Showing all jobs — use the filter below.")
            else:
                st.error(result.get("error", "Something went wrong."))
        st.caption("Resumes are analysed by Google's free-tier AI.")
    else:
        st.caption("Resume matching needs: pip install pypdf google-genai")


# ── UNIVERSITY BANNER ─────────────────────────────────────────────────────────
qs_html = (f'<div class="qs-badge"><span class="label">QS World 2026</span>'
           f'<span class="num">#{uni["qs"]}</span></div>') if uni.get("qs") else \
          '<div class="qs-badge"><span class="label">QS World 2026</span><span class="num">—</span></div>'
st.markdown(f"""
<div class="uni-banner">
  <div>
    <div class="uni-name">{uni['name']}</div>
    <div class="uni-loc">📍 {uni['city']}, {uni['state']} · {uni['region']}</div>
  </div>
  {qs_html}
</div>
""", unsafe_allow_html=True)


# ── MODE FRAMING NOTE ─────────────────────────────────────────────────────────
if not has_employers:
    st.info(f"**{uni['name']}** is in our directory, but its employer list "
            f"hasn't been compiled yet.")
    st.stop()

if mode == "alumni":
    st.markdown(f"#### Where {uni['name']} graduates commonly work")
    st.caption("Curated from public graduate-destination and regional employment sources.")
else:
    st.markdown(f"#### Major graduate employers in {uni['region']}")
    st.caption("These are the state's largest graduate employers — a useful starting "
               "point, but not a verified alumni list for this specific university.")


# ── FETCH JOBS ──────────────────────────────────────────────────────────────--
with st.spinner("Fetching live jobs..."):
    if chosen_employer == "All employers":
        all_jobs = []
        for emp in uni["employers"]:
            all_jobs.extend(fetch_jobs(emp["name"], uni["region"], max_results=15))
    else:
        all_jobs = fetch_jobs(chosen_employer, uni["region"], max_results=30)

seen, jobs = set(), []
for j in all_jobs:
    if j["url"] and j["url"] not in seen:
        seen.add(j["url"]); jobs.append(j)


# ── INTEREST FILTER ───────────────────────────────────────────────────────────
cat_counts = {}
for j in jobs:
    cat_counts[j["category"]] = cat_counts.get(j["category"], 0) + 1
cat_options = sorted(cat_counts.keys(), key=lambda c: -cat_counts[c])

st.markdown('<div class="section-label">Filter by area of interest</div>', unsafe_allow_html=True)

# if a resume was uploaded, pre-select its categories (only those present in results)
default_cats = [c for c in resume_cats if c in cat_options]
if default_cats:
    st.caption(f"✨ Pre-filtered to your resume match. Clear the tags to see all {len(jobs)} jobs.")

chosen_cats = st.multiselect(
    "interest", options=cat_options,
    format_func=lambda c: f"{c} ({cat_counts[c]})",
    default=default_cats, label_visibility="collapsed",
    help="Leave empty to see every area. Counts show jobs per category.",
)
visible = [j for j in jobs if j["category"] in chosen_cats] if chosen_cats else jobs

# newest first
visible.sort(key=lambda j: j["created"], reverse=True)


# ── RESULTS ─────────────────────────────────────────────────────────────────--
st.markdown(f'<div class="section-label">Results</div>', unsafe_allow_html=True)
st.markdown(f'<span class="count-big">{len(visible)}</span> '
            f'<span style="color:var(--muted)">live job{"s" if len(visible)!=1 else ""}'
            f'{" at " + chosen_employer if chosen_employer != "All employers" else ""}</span>',
            unsafe_allow_html=True)
st.write("")

if not visible:
    st.info("No jobs match this filter right now. Try removing the interest filter, "
            "or choose **All employers** in the sidebar.")
else:
    for j in visible:
        col1, col2 = st.columns([5, 1])
        with col1:
            st.markdown(f"""
            <div class="job-card">
              <div class="job-title">{j['title']}</div>
              <div class="job-employer">{j['employer'] or j['matched_employer']}</div>
              <div class="job-meta">
                <span class="cat-pill">{j['category']}</span>
                🕒 {j['contract']} &nbsp;·&nbsp; 📍 {j['location']}
                {('&nbsp;·&nbsp; posted ' + j['created']) if j['created'] else ''}
              </div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.write(""); st.write("")
            st.link_button("Apply ↗", j["url"], use_container_width=True)

# ── GROW YOUR SKILLS ──────────────────────────────────────────────────────────
# Drive the panel off the resume match first (most personalised), else off the
# user's chosen interest filters. Only categories we've curated courses for show.
growth_source = resume_cats if resume_cats else chosen_cats
if growth_source:
    st.write("")
    render_growth_panel(growth_source)

st.markdown(f"""
<div class="site-footer">
  <div class="rule-thin"></div>
  <div class="rule-thick"></div>
  <div class="footer-row">
    <div class="footer-credits">Employer data compiled from public sources ·
      Job listings via the Adzuna API · QS World University Rankings 2026 ·
      “Apply” opens the original posting.</div>
    <a class="kofi-btn" href="{KOFI_URL}" target="_blank" rel="noopener">☕ Support on Ko-fi</a>
  </div>
  <div class="footer-note">Built by Harsh Rastogi — a smarter, honest way to start a graduate job search.</div>
</div>
""", unsafe_allow_html=True)
