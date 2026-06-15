"""
Gradaroo. Find jobs where your university's graduates actually work.

Run locally:   streamlit run app.py
Needs:         pip install streamlit requests pypdf
Data file:     employers.json  (must sit next to this file)
"""

import os
import html
import json
import logging
import requests
import streamlit as st

# resume parsing is optional - app still runs if these aren't installed
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

# Server-side logger. User-facing errors stay generic; details go here only.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gradaroo")

# Hard cap on resume upload size (bytes) before we hand the PDF to pypdf.
# Protects the free-tier host from oversized / malicious PDFs.
MAX_RESUME_BYTES = 5 * 1024 * 1024  # 5 MB


def safe(value):
    """HTML-escape any externally-sourced string before it goes into
    st.markdown(..., unsafe_allow_html=True). Anything from the jobs API,
    the resume, or the LLM is untrusted and must pass through here."""
    return html.escape(str(value if value is not None else ""))


def safe_url(url):
    """Allow only http(s) links through to hrefs. Blocks javascript:, data:,
    and other script-bearing schemes. Returns '#' for anything suspicious."""
    u = str(url or "").strip()
    if u.lower().startswith(("https://", "http://")):
        return html.escape(u, quote=True)
    return "#"


# ── RESUME ENGINE (Gemini-powered) ────────────────────────────────────────────
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
- Judge by their ACTUAL skills, projects, and interests - NOT just their degree.
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
    size = getattr(uploaded_file, "size", None)
    if size is not None and size > MAX_RESUME_BYTES:
        return {"ok": False, "error": "That PDF is too large (max 5 MB)."}

    if not PYPDF_OK:
        return {"ok": False, "error": "pypdf not installed"}
    try:
        reader = PdfReader(uploaded_file)
        text = "\n".join((p.extract_text() or "") for p in reader.pages)
    except Exception:
        return {"ok": False, "error": "Couldn't read that PDF."}
    if len(text.strip()) < 30:
        return {"ok": False, "error": "No readable text found (scanned image?)."}

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
            if "503" in last_err or "429" in last_err or "UNAVAILABLE" in last_err:
                time.sleep(2 * (attempt + 1))
                continue
            logger.warning("Gemini analysis failed: %s", last_err)
            return {"ok": False, "error": "AI analysis failed. Please try again."}
    return {"ok": False, "error": "Matching is busy right now. Please try again in a moment."}

# ── API CREDENTIALS ───────────────────────────────────────────────────────────
def get_secret(key, default):
    val = os.environ.get(key)
    if val:
        return val
    try:
        return st.secrets[key]
    except Exception:
        return default

APP_ID = get_secret("ADZUNA_APP_ID", "")
APP_KEY = get_secret("ADZUNA_APP_KEY", "")
GEMINI_KEY = get_secret("GEMINI_API_KEY", "")
ADZUNA_URL = "https://api.adzuna.com/v1/api/jobs/au/search/1"
KOFI_URL = "https://ko-fi.com/harshrastogi"

def _keys_missing():
    return not APP_ID or not APP_KEY


# ── COURSE CATALOG ────────────────────────────────────────────────────────────
COURSE_CATALOG = {
    "IT Jobs": {
        "free": [("freeCodeCamp · full coding & data curriculum", "https://www.freecodecamp.org/learn"),
                 ("Kaggle Learn · hands-on data science", "https://www.kaggle.com/learn")],
        "paid": [("Google Data Analytics Certificate (Coursera)", "https://www.coursera.org/professional-certificates/google-data-analytics"),
                 ("Python courses (Udemy)", "https://www.udemy.com/topic/python/")],
    },
    "PR, Advertising & Marketing Jobs": {
        "free": [("HubSpot Academy · free marketing certs", "https://academy.hubspot.com/courses"),
                 ("Google Skillshop · Ads & Analytics", "https://skillshop.withgoogle.com/")],
        "paid": [("Google Digital Marketing Certificate (Coursera)", "https://www.coursera.org/professional-certificates/google-digital-marketing-ecommerce"),
                 ("Digital marketing courses (Udemy)", "https://www.udemy.com/topic/digital-marketing/")],
    },
    "Accounting & Finance Jobs": {
        "free": [("Khan Academy · finance & economics", "https://www.khanacademy.org/economics-finance-domain"),
                 ("Xero training (widely used in AU)", "https://www.xero.com/au/training/")],
        "paid": [("Finance courses (Coursera)", "https://www.coursera.org/browse/business/finance"),
                 ("Accounting courses (Udemy)", "https://www.udemy.com/topic/accounting/")],
    },
    "Admin Jobs": {
        "free": [("Microsoft Learn · Office & productivity", "https://learn.microsoft.com/training/")],
        "paid": [("Excel courses (Udemy)", "https://www.udemy.com/topic/excel/")],
    },
    "Engineering Jobs": {
        "free": [("MIT OpenCourseWare · engineering", "https://ocw.mit.edu/")],
        "paid": [("AutoCAD courses (Udemy)", "https://www.udemy.com/topic/autocad/")],
    },
    "Healthcare & Nursing Jobs": {
        "free": [("FutureLearn · healthcare courses", "https://www.futurelearn.com/subjects/healthcare-medicine-courses")],
        "paid": [("Health courses (Coursera)", "https://www.coursera.org/browse/health")],
    },
    "Teaching Jobs": {
        "free": [("FutureLearn · teaching courses", "https://www.futurelearn.com/subjects/teaching-courses")],
        "paid": [("Education courses (Coursera)", "https://www.coursera.org/browse/social-sciences/education")],
    },
    "Sales Jobs": {
        "free": [("HubSpot Academy · free sales training", "https://academy.hubspot.com/courses?topic=sales")],
        "paid": [("Sales courses (Udemy)", "https://www.udemy.com/topic/sales-skills/")],
    },
    "Customer Services Jobs": {
        "free": [("HubSpot Academy · service training", "https://academy.hubspot.com/courses?topic=service")],
        "paid": [("Customer service courses (Udemy)", "https://www.udemy.com/topic/customer-service/")],
    },
    "Creative & Design Jobs": {
        "free": [("Canva Design School", "https://www.canva.com/designschool/")],
        "paid": [("Design courses (Skillshare)", "https://www.skillshare.com/en/browse/design")],
    },
}

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
    shown = [c for c in matched_cats if c in COURSE_CATALOG][:max_cards]
    if not shown:
        return

    def _row(label, url, is_free):
        tag = "Free" if is_free else "Paid"
        tag_cls = "tag-free" if is_free else "tag-paid"
        return (
            f'<a class="course-row" href="{safe_url(url)}" target="_blank" rel="noopener">'
            f'<span class="course-label"><span class="course-tag {tag_cls}">{tag}</span>'
            f'{safe(label)}</span><span class="course-ext">↗</span></a>'
        )

    cards = []
    for cat in shown:
        opts = COURSE_CATALOG[cat]
        icon = CATEGORY_ICONS.get(cat, "🌱")
        rows = "".join(_row(l, u, True) for l, u in opts.get("free", []))
        rows += "".join(_row(l, u, False) for l, u in opts.get("paid", []))
        nice = cat[:-5] if cat.endswith(" Jobs") else cat
        cards.append(
            f'<div class="grow-card"><div class="grow-card-head">'
            f'<span class="grow-card-icon">{icon}</span>'
            f'<span class="grow-card-title">{safe(nice)}</span></div>'
            f'<div class="grow-rows">{rows}</div></div>'
        )

    st.markdown(f"""
<div class="grow-panel">
<div class="grow-head">
<span class="grow-seed">🌱</span>
<span class="grow-title">Grow your skills</span>
</div>
<div class="grow-sub">Free options are genuinely free. Paid courses include a
shareable certificate, which helps prove the skill to employers. Pick whatever
fits your budget. These are plain links; we earn nothing from them.</div>
<div class="grow-grid">{''.join(cards)}</div>
<div class="grow-support">Gradaroo is free and earns nothing from these links.
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
        logger.warning("Adzuna fetch failed for %s: %s", employer_name, e)
        st.error(f"Couldn't fetch jobs for {safe(employer_name)} right now.")
        return []
    jobs = []
    for j in raw:
        jobs.append({
            "title": safe(j.get("title", "")),
            "employer": safe(j.get("company", {}).get("display_name", "")),
            "category": safe(j.get("category", {}).get("label", "Other/General Jobs")),
            "location": safe(j.get("location", {}).get("display_name", "")),
            "contract": safe((j.get("contract_time") or "n/a").replace("_", "-")),
            "created": safe(j.get("created", "")[:10]),
            "url": j.get("redirect_url", ""),
            "matched_employer": safe(employer_name),
        })
    return jobs


# ── PAGE CONFIG ─────────────────────────────────────────────────────────────--
st.set_page_config(page_title="Gradaroo", page_icon="🎓",
                   layout="centered", initial_sidebar_state="collapsed")

# ── HIDE STREAMLIT CHROME + SAFE BOOT COVER ───────────────────────────────────
# Runs on every rerun. Two jobs:
#  1) Hide Streamlit's sidebar/chevron/toolbar so the app reads as a clean site.
#  2) A PURE-CSS boot cover (::before pseudo-element on the app container) paints
#     a branded screen over Streamlit's bare boot frame, then fades itself out via
#     a CSS animation. It is pseudo-element only — it adds NO real DOM node, so
#     React has nothing extra to reconcile or detach. This is deliberately simple:
#     an earlier JS-based curtain crashed React's render cycle, so we use CSS only.
st.markdown("""
<style>
[data-testid="stSidebarNav"] { display: none; }
[data-testid="stSidebar"] { display: none; }
[data-testid="stSidebarCollapsedControl"] { display: none; }
[data-testid="collapsedControl"] { display: none; }
[data-testid="stToolbar"] { display: none; }
[data-testid="stStatusWidget"] { display: none; }
[data-testid="stDecoration"] { display: none; }
header { display: none; }

/* --- Branded boot cover (CSS-only, pseudo-elements; no JS, no DOM nodes) --- */
@keyframes gr-boot-fade {
  0%   { opacity: 1; visibility: visible; }
  82%  { opacity: 1; visibility: visible; }
  100% { opacity: 0; visibility: hidden; }
}
@keyframes gr-boot-spin { to { transform: rotate(360deg); } }

/* The cover sits on the app container's ::before, fixed to the viewport. It
   plays once for ~2.6s then fades to hidden and stops (forwards), after which
   pointer-events are gone and the app is fully interactive. */
[data-testid="stAppViewContainer"]::before {
  content: "Gradaroo";
  position: fixed; inset: 0; z-index: 9999;
  display: flex; align-items: center; justify-content: center;
  background: #faf6f0;
  background-image: radial-gradient(circle at 50% 40%, #fff5ed 0%, #faf6f0 60%);
  font-family: 'Newsreader', Georgia, serif;
  font-size: 42px; font-weight: 600; letter-spacing: -0.02em; color: #1c1917;
  animation: gr-boot-fade 2.6s ease forwards;
  pointer-events: none;
}
/* Spinner ring above the wordmark via ::after. */
[data-testid="stAppViewContainer"]::after {
  content: "";
  position: fixed; left: 50%; top: calc(50% - 56px);
  width: 34px; height: 34px; margin-left: -17px;
  border: 3px solid rgba(188,69,20,0.18);
  border-top-color: #bc4514;
  border-radius: 50%;
  z-index: 10000;
  animation: gr-boot-spin 0.9s linear infinite, gr-boot-fade 2.6s ease forwards;
  pointer-events: none;
}
@media (prefers-reduced-motion: reduce) {
  [data-testid="stAppViewContainer"]::before,
  [data-testid="stAppViewContainer"]::after { animation: gr-boot-fade 1.2s ease forwards; }
  [data-testid="stAppViewContainer"]::after { border-top-color: rgba(188,69,20,0.18); }
}
</style>
""", unsafe_allow_html=True)

# ── CUSTOM STYLING ────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Libre+Franklin:wght@400;500;600;700;800&family=Newsreader:opsz,wght@6..72,400;6..72,500;6..72,600&display=swap');

:root {
  --ink: #1c1917;
  --paper: #faf6f0;
  --card: #ffffff;
  --accent: #bc4514;
  --accent-2: #e8742c;
  --grad: linear-gradient(135deg, #bc4514 0%, #e8742c 100%);
  --grad-soft: linear-gradient(135deg, #f9ece2 0%, #fff5ed 100%);
  --accent-soft: #f9ece2;
  --line: #ece3d6;
  --muted: #756c5f;
  --shadow-sm: 0 1px 2px rgba(28,25,23,.05), 0 4px 14px rgba(28,25,23,.06);
  --shadow-md: 0 4px 10px rgba(28,25,23,.07), 0 16px 36px rgba(28,25,23,.11);
  --shadow-lift: 0 10px 24px rgba(122,36,10,.10), 0 24px 60px rgba(122,36,10,.14);
  /* One shared easing + timing, identical to the landing page, so the app and
     the marketing site move with the same "feel" (see UX review: seamless handoff). */
  --ease: cubic-bezier(0.4, 0, 0.2, 1);
  --t-fast: 0.16s var(--ease);
  --t-med: 0.3s var(--ease);
}

/* ── SHARED MOTION LANGUAGE ────────────────────────────────────────────────
   Content rises gently into place on first paint. The whole app uses ONE
   keyframe + easing so every section breathes the same way. Staggered delays
   make the page assemble top-to-bottom instead of popping in all at once.
   All of this is opacity/transform only — GPU-cheap, and it cannot touch
   React's DOM reconciliation, so it can't reintroduce the old crash class. */
@keyframes gr-rise {
  from { opacity: 0; transform: translateY(16px); }
  to   { opacity: 1; transform: none; }
}
@keyframes gr-rise-sm {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: none; }
}
@keyframes gr-pop {
  0%   { opacity: 0; transform: scale(.96) translateY(8px); }
  60%  { opacity: 1; }
  100% { opacity: 1; transform: scale(1) translateY(0); }
}

/* Reveal helper applied to major sections via wrapper markup. */
.gr-reveal { animation: gr-rise .55s var(--ease) both; }

.stApp { background: var(--paper); }
html { font-size: 88%; }
.stApp, [data-testid="stAppViewContainer"] { font-size: 14px; }
.block-container { max-width: 1050px; padding-top: 2rem; }
html, body, [class*="css"], .stMarkdown, p, span, div, label {
  font-family: 'Libre Franklin', -apple-system, sans-serif;
  color: var(--ink);
}

/* ---- TOP BAR ---- */
.topbar { display: flex; justify-content: space-between; align-items: center; padding: 4px 0 8px; }
.topbar .wordmark {
  font-family: 'Newsreader', Georgia, serif; font-size: 30px; font-weight: 600;
  letter-spacing: -0.02em; color: var(--ink); text-decoration: none !important;
}
.topbar .wordmark .go { color: var(--accent); font-style: italic; }
.topbar-links { display: flex; align-items: center; gap: 18px; }
.topnav-link { color: var(--ink) !important; font-size: 14px; font-weight: 600;
  text-decoration: none !important; transition: color .14s ease; }
.topnav-link:hover { color: var(--accent) !important; }
.kofi-btn {
  display: inline-flex; align-items: center; gap: 7px; white-space: nowrap;
  background: var(--ink); color: #ffffff !important; text-decoration: none !important;
  border-radius: 999px; padding: 9px 19px; font-size: 13px; font-weight: 600;
  transition: all .16s ease;
}
.kofi-btn:hover { background: var(--grad); transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(188,69,20,.35); }

/* ---- HERO ---- */
.hero-wrap { text-align: center; padding: 30px 0 6px; animation: rise .6s ease both; }
.hero-chip {
  display: inline-flex; align-items: center; gap: 8px;
  background: var(--card); border: 1px solid var(--line); box-shadow: var(--shadow-sm);
  border-radius: 999px; padding: 7px 16px;
  font-size: 12px; font-weight: 600; letter-spacing: .04em; color: var(--muted);
}
.hero-chip .live-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--grad); }
.hero-wrap h1 {
  font-family: 'Newsreader', Georgia, serif; font-weight: 500; font-size: 50px;
  line-height: 1.08; letter-spacing: -0.025em; color: var(--ink);
  margin: 18px auto 0; max-width: 760px;
}
.hero-wrap h1 em { font-style: italic; color: var(--accent); }
.hero-sub {
  font-size: 16px; color: var(--muted); line-height: 1.65;
  margin: 14px auto 0; max-width: 600px;
}
@keyframes rise { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: none; } }

/* ---- STAT STRIP ---- */
.stat-strip { display: flex; justify-content: center; margin: 24px auto 2px; max-width: 660px; }
.stat { flex: 1; padding: 2px 18px; text-align: center; }
.stat + .stat { border-left: 1px solid var(--line); }
.stat .n { font-family: 'Newsreader', serif; font-size: 28px; font-weight: 600; color: var(--ink); }
.stat .n em { font-style: italic; color: var(--accent); }
.stat .l { font-size: 10.5px; text-transform: uppercase; letter-spacing: .14em;
  color: var(--muted); font-weight: 700; margin-top: 3px; }

/* ---- STEP CHIPS ---- */
.step-chips { display: flex; justify-content: center; align-items: center; flex-wrap: wrap;
  gap: 10px; margin: 22px 0 6px; }
.step-chip {
  display: inline-flex; align-items: center; gap: 9px;
  background: var(--card); border: 1px solid var(--line); box-shadow: var(--shadow-sm);
  border-radius: 999px; padding: 8px 17px; font-size: 13px; font-weight: 600; color: var(--ink);
  transition: all .18s ease;
}
.step-chip:hover { border-color: var(--accent-2); transform: translateY(-1px); box-shadow: var(--shadow-md); }
.step-chip .n {
  width: 20px; height: 20px; border-radius: 50%; background: var(--grad); color: #fff;
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 700;
}
.step-arrow { color: var(--muted); font-size: 14px; }

/* ============================================================================
   SMART MATCH  —  single unified card (FIX 1, 2, 3)
   The whole section is ONE Streamlit container. We anchor on .smart-match-root
   and style the container that DIRECTLY contains it, so the header, uploader,
   results and security note all sit inside one bordered, rounded card with no
   empty second box and no white gap.
   ============================================================================ */

/* The vertical block whose DIRECT child element-container holds our anchor
   becomes the card. The '>' is important: it matches ONLY the immediate
   wrapping container (the one created by st.container()), not every ancestor
   block up the page — so the rest of the page is untouched. */
[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] > .smart-match-root) {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 20px;
  box-shadow: var(--shadow-sm);
  padding: 22px 24px;
  transition: box-shadow var(--t-med), transform var(--t-med), border-color var(--t-med);
  animation: gr-rise .55s var(--ease) both;
}
[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] > .smart-match-root):hover {
  box-shadow: var(--shadow-lift);
  transform: translateY(-2px);
  border-color: rgba(232,116,44,.32);
}

/* The anchor itself must take no space (kills the white gap / empty box). */
.smart-match-root { display: none; }
[data-testid="stElementContainer"]:has(> .smart-match-root) {
  margin: 0 !important;
  padding: 0 !important;
  min-height: 0 !important;
  height: 0 !important;
}

/* Header row inside the card */
.smart-match-header {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 16px;
}
.smart-match-icon {
  font-size: 24px;
  width: 46px;
  height: 46px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--grad);
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(188,69,20,.25);
  position: relative;
  overflow: hidden;
}
/* A single slow sheen sweeps across the AI tile every few seconds — just enough
   to read as "alive / intelligent" without becoming busy. One accent, used once. */
.smart-match-icon::after {
  content: "";
  position: absolute; top: 0; left: -120%;
  width: 80%; height: 100%;
  background: linear-gradient(100deg, transparent 0%, rgba(255,255,255,.45) 50%, transparent 100%);
  transform: skewX(-18deg);
  animation: gr-sheen 4.5s var(--ease) infinite;
}
@keyframes gr-sheen {
  0%, 62% { left: -120%; }
  82%, 100% { left: 160%; }
}
.smart-match-header-text { flex: 1; min-width: 0; }
.smart-match-title {
  font-family: 'Newsreader', serif;
  font-size: 19px;
  font-weight: 600;
  color: var(--ink);
}
.smart-match-subtitle {
  font-size: 13px;
  color: var(--muted);
  margin-top: 2px;
  line-height: 1.45;
}

/* File Uploader Styling (integrated, no extra outer chrome) */
[data-testid="stFileUploader"] { margin: 0 0 4px 0; }
[data-testid="stFileUploader"] section,
[data-testid="stFileUploaderDropzone"] {
  background: var(--grad-soft) !important;
  border: 2px dashed var(--accent-2) !important;
  border-radius: 16px !important;
  min-height: 110px !important;
  padding: 18px !important;
  display: flex !important;
  flex-direction: column !important;
  align-items: center !important;
  justify-content: center !important;
  transition: all .2s ease !important;
  margin: 0 !important;
}
[data-testid="stFileUploader"] section:hover,
[data-testid="stFileUploaderDropzone"]:hover {
  border-color: var(--accent) !important;
  background: var(--accent-soft) !important;
}
[data-testid="stFileUploader"] section * { color: var(--ink) !important; }

/* FIX 2: upload "Browse files" button — white text on the gradient, forced on
   every child node (Streamlit nests the label in <p>/<span>/<div>). */
[data-testid="stFileUploader"] button,
[data-testid="stBaseButton-secondary"] {
  background: var(--grad) !important;
  border: none !important;
  border-radius: 999px !important;
  font-weight: 600 !important;
  padding: 8px 22px !important;
  box-shadow: 0 4px 12px rgba(188,69,20,.25) !important;
  transition: all .2s ease !important;
  margin-top: 8px !important;
}
[data-testid="stFileUploader"] button,
[data-testid="stFileUploader"] button *,
[data-testid="stFileUploader"] button p,
[data-testid="stFileUploader"] button span,
[data-testid="stFileUploader"] button div {
  color: #ffffff !important;
  -webkit-text-fill-color: #ffffff !important;
  fill: #ffffff !important;
}
[data-testid="stFileUploader"] button:hover {
  transform: translateY(-1px) !important;
  box-shadow: 0 6px 16px rgba(188,69,20,.35) !important;
}
[data-testid="stFileUploaderFile"] {
  background: var(--paper) !important;
  border: 1px solid var(--line) !important;
  border-radius: 12px !important;
  padding: 12px 16px !important;
  margin: 12px 0 0 0 !important;
}
[data-testid="stFileUploaderFile"] * { color: var(--ink) !important; }
/* the little delete (x) icon button on the uploaded-file chip stays neutral */
[data-testid="stFileUploaderDeleteBtn"] button { background: transparent !important; box-shadow: none !important; }
[data-testid="stFileUploaderDeleteBtn"] button * { color: var(--muted) !important; -webkit-text-fill-color: var(--muted) !important; fill: var(--muted) !important; }

/* Analysis States */
.analysis-loading {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 18px 22px;
  background: var(--grad-soft);
  border-radius: 14px;
  margin: 14px 0 2px;
  border: 1px solid var(--line);
}
.loading-spinner {
  width: 30px;
  height: 30px;
  border: 3px solid rgba(188,69,20,0.15);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  flex-shrink: 0;
}
.loading-text { font-size: 15px; font-weight: 600; color: var(--ink); }
@keyframes spin { to { transform: rotate(360deg); } }

.analysis-success {
  background: linear-gradient(135deg, #f0f7f0 0%, #f5faf5 100%);
  border: 1px solid #c6e4c6;
  border-radius: 16px;
  padding: 20px 22px;
  margin: 14px 0 2px;
  animation: gr-pop .42s var(--ease) both;
}
/* The emotional peak of the app: each part of the result reveals in sequence
   (header → pill → summary → tags), so the match feels "assembled for you"
   rather than dumped on screen. This is the deliberate, reserved flourish. */
.analysis-success > * { animation: gr-rise-sm .4s var(--ease) both; }
.analysis-success > *:nth-child(1) { animation-delay: .05s; }
.analysis-success > *:nth-child(2) { animation-delay: .13s; }
.analysis-success > *:nth-child(3) { animation-delay: .21s; }
.analysis-success > *:nth-child(4) { animation-delay: .29s; }
.analysis-success > *:nth-child(5) { animation-delay: .37s; }
@keyframes popIn { from { opacity: 0; transform: scale(0.98); } to { opacity: 1; transform: scale(1); } }
.success-header { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.success-icon {
  font-size: 18px; width: 30px; height: 30px;
  display: flex; align-items: center; justify-content: center;
  background: #2f6b34; border-radius: 50%; color: white;
  animation: gr-check-pop .5s var(--ease) both .1s;
}
@keyframes gr-check-pop {
  0% { transform: scale(0); }
  70% { transform: scale(1.15); }
  100% { transform: scale(1); }
}
.success-icon * { color: #fff !important; }
.success-title { font-weight: 700; font-size: 16px; color: #2f6b34; }
.best-match-pill {
  display: inline-flex; align-items: center; gap: 8px;
  background: var(--grad); color: white; font-weight: 700; font-size: 16px;
  padding: 10px 18px; border-radius: 999px; margin: 8px 0 14px;
  box-shadow: 0 6px 18px rgba(188,69,20,.3);
}
.best-match-pill, .best-match-pill * { color: #fff !important; -webkit-text-fill-color: #fff !important; }
.match-summary {
  font-style: italic; color: #2f6b34;
  background: rgba(47,107,52,0.05); border-left: 3px solid #2f6b34;
  padding: 12px 16px; border-radius: 0 10px 10px 0; margin: 12px 0;
  font-size: 14px; line-height: 1.6;
}
.matched-cats-list { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }
.matched-cat-tag {
  background: white; border: 1px solid #c6e4c6; color: #2f6b34;
  padding: 6px 12px; border-radius: 999px; font-size: 12.5px; font-weight: 600;
  transition: transform var(--t-fast), box-shadow var(--t-fast), border-color var(--t-fast);
}
.matched-cat-tag:hover {
  transform: translateY(-2px);
  border-color: #2f6b34;
  box-shadow: 0 4px 12px rgba(47,107,52,.18);
}

.analysis-warning {
  background: #fff9e6; border: 1px solid #f0c85c; border-radius: 16px;
  padding: 16px 20px; margin: 14px 0 2px;
  display: flex; align-items: flex-start; gap: 12px;
}
.analysis-error {
  background: #fff0f0; border: 1px solid #e8b4b4; border-radius: 16px;
  padding: 16px 20px; margin: 14px 0 2px;
  display: flex; align-items: flex-start; gap: 12px;
}
.state-icon { font-size: 18px; flex-shrink: 0; margin-top: 2px; }
.state-text { font-size: 14px; line-height: 1.5; }

/* Security Note */
.security-note {
  display: flex; align-items: center; gap: 8px;
  margin-top: 14px; padding: 12px 16px;
  background: var(--paper); border: 1px solid var(--line); border-radius: 12px;
  font-size: 12.5px; color: var(--muted);
}
.security-icon { font-size: 16px; color: var(--accent); flex-shrink: 0; }

/* setup hint (deps missing) */
.setup-hint { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
.setup-hint-title { font-weight: 700; font-size: 16px; color: var(--ink); }
.setup-code {
  margin-top: 10px; padding: 12px 16px; background: var(--paper);
  border: 1px solid var(--line); border-radius: 10px;
  font-family: monospace; font-size: 13px; color: var(--ink);
}

/* ---- UNIVERSITY BANNER ---- */
.uni-banner {
  background: linear-gradient(135deg, #1c1917 0%, #33241a 100%);
  border-radius: 20px; box-shadow: var(--shadow-md);
  padding: 24px 28px; margin: 24px 0 8px;
  display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;
  position: relative; overflow: hidden;
  animation: gr-rise .5s var(--ease) both;
}
/* A barely-there warm glow drifts behind the banner — adds depth on the dark
   surface without reading as an "effect". Slow enough to be felt, not watched. */
.uni-banner::before {
  content: ""; position: absolute; inset: -40% -10%;
  background: radial-gradient(circle at 30% 40%, rgba(232,116,44,.14) 0%, transparent 55%);
  pointer-events: none;
  animation: gr-glow-drift 11s ease-in-out infinite alternate;
}
@keyframes gr-glow-drift {
  0%   { transform: translate(0, 0) scale(1); }
  100% { transform: translate(8%, 6%) scale(1.12); }
}
.uni-banner > * { position: relative; z-index: 1; }
.uni-banner .uni-name {
  font-family: 'Newsreader', serif; font-size: 25px; font-weight: 600; color: #ffffff;
}
.uni-banner .uni-loc { color: #b8b0a4; font-size: 13.5px; margin-top: 4px; }
.qs-badge {
  background: var(--grad); color: #fff; border-radius: 14px;
  box-shadow: 0 8px 22px rgba(188,69,20,.40);
  padding: 9px 18px; text-align: center; white-space: nowrap;
  transition: transform var(--t-med), box-shadow var(--t-med);
}
.uni-banner:hover .qs-badge { transform: translateY(-2px) scale(1.03); box-shadow: 0 12px 28px rgba(188,69,20,.5); }
.qs-badge .label { font-size: 9.5px; text-transform: uppercase; letter-spacing: 0.13em; opacity: 0.9; display:block; color:#fff; }
.qs-badge .num { font-size: 19px; font-weight: 700; color:#fff; }

/* ---- JOB CARD ---- */
.job-card {
  background: var(--card); border: 1px solid var(--line); border-radius: 16px;
  border-left: 3px solid transparent;
  box-shadow: var(--shadow-sm);
  padding: 20px 22px; margin-bottom: 14px;
  transition: transform var(--t-med), box-shadow var(--t-med), border-color var(--t-med);
  animation: gr-rise-sm .45s var(--ease) both;
}
.job-card:hover { border-left-color: var(--accent-2);
  transform: translateY(-4px); box-shadow: var(--shadow-lift); }
.job-title { font-family: 'Newsreader', serif; font-size: 20px; font-weight: 600;
  line-height: 1.25; margin: 0 0 3px; color: var(--ink); transition: color var(--t-fast); }
.job-card:hover .job-title { color: var(--accent); }
.job-employer { font-weight: 600; font-size: 13.5px; color: var(--accent); margin-bottom: 9px; }
.job-meta { font-size: 12.5px; color: var(--muted); }
.cat-pill {
  display: inline-block; background: var(--accent-soft); color: var(--accent);
  border-radius: 999px; padding: 3px 11px; font-size: 11.5px; font-weight: 600; margin-right: 6px;
}

/* ---- SECTION LABELS ---- */
.section-label {
  display: flex; align-items: center; gap: 12px;
  font-size: 11px; text-transform: uppercase; letter-spacing: 0.15em;
  color: var(--muted); font-weight: 700; margin: 24px 0 12px;
  animation: gr-rise-sm .45s var(--ease) both;
}
.section-label::after {
  content: ""; flex: 1; height: 1px; background: var(--line);
  transform-origin: left; animation: gr-line-draw .6s var(--ease) both .1s;
}
@keyframes gr-line-draw { from { transform: scaleX(0); } to { transform: scaleX(1); } }
.count-big { font-family: 'Newsreader', serif; font-size: 32px; font-weight: 600; color: var(--ink); }

/* ---- LINK BUTTON ---- */
.stLinkButton a {
  background: var(--ink) !important; color: #ffffff !important;
  border: none !important; border-radius: 999px !important; font-weight: 600 !important;
  transition: transform var(--t-fast), box-shadow var(--t-fast), background var(--t-fast) !important;
}
.stLinkButton a:hover { background: var(--grad) !important; color:#fff !important;
  box-shadow: 0 6px 18px rgba(188,69,20,.35) !important;
  transform: translateY(-1px) !important; }
.stLinkButton a:active { transform: translateY(0) scale(.98) !important; }
.stLinkButton a p { color:#ffffff !important; }

@media (min-width: 769px) {
  [data-testid="stHorizontalBlock"]:has(.job-card) .stLinkButton { margin-top: 30px; }
}
@media (max-width: 768px) {
  [data-testid="stHorizontalBlock"]:has(.job-card) .stLinkButton { margin-top: 0 !important; margin-bottom: 4px; }
  [data-testid="stHorizontalBlock"]:has(.job-card) .job-card { margin-bottom: 8px !important; }
  [data-testid="stHorizontalBlock"]:has(.job-card) + [data-testid="stHorizontalBlock"] { margin-top: 20px; }
}

/* ---- DROPDOWN STYLING ---- */
[data-baseweb="popover"] { background: #ffffff !important; }
[data-baseweb="popover"] li, [data-baseweb="popover"] [role="option"],
[data-baseweb="menu"] li, ul[role="listbox"] li {
  color: var(--ink) !important; background: #ffffff !important;
}
[data-baseweb="popover"] li:hover, [data-baseweb="popover"] [role="option"]:hover,
ul[role="listbox"] li:hover {
  background: var(--accent-soft) !important; color: var(--accent) !important;
}

/* FIX 4: multiselect chosen tags — accent background with WHITE text on every
   child node (label + the little close 'x' svg), for proper contrast. */
[data-baseweb="tag"] {
  background: var(--accent) !important;
  border-radius: 999px !important;
}
[data-baseweb="tag"],
[data-baseweb="tag"] *,
[data-baseweb="tag"] span,
[data-baseweb="tag"] div {
  color: #ffffff !important;
  -webkit-text-fill-color: #ffffff !important;
}
[data-baseweb="tag"] svg { fill: #ffffff !important; color: #ffffff !important; }
[data-baseweb="tag"] [role="button"]:hover { background: rgba(255,255,255,0.22) !important; }

[data-baseweb="select"] > div {
  background: #ffffff !important;
  border: 1px solid var(--line) !important;
  border-radius: 12px !important;
  box-shadow: var(--shadow-sm) !important;
  transition: all .2s ease !important;
}
[data-baseweb="select"] > div:focus-within { border-color: var(--accent-2) !important;
  box-shadow: 0 0 0 3px rgba(232,116,44,0.15) !important; }
[data-baseweb="select"] > div > div, [data-baseweb="select"] span {
  color: var(--ink) !important; -webkit-text-fill-color: var(--ink) !important;
}
/* but keep the chosen-tag text white even though it lives inside the select */
[data-baseweb="select"] [data-baseweb="tag"] span {
  color: #ffffff !important; -webkit-text-fill-color: #ffffff !important;
}

/* ---- GROW YOUR SKILLS PANEL ---- */
.grow-panel {
  background: var(--card); border: 1px solid var(--line); border-radius: 20px;
  box-shadow: var(--shadow-sm); padding: 24px 26px; margin: 10px 0 4px;
}
.grow-head { display: flex; align-items: center; gap: 9px; margin-bottom: 6px; }
.grow-seed { font-size: 20px; line-height: 1; }
.grow-title {
  font-family: 'Newsreader', serif; font-size: 23px; font-weight: 600; color: var(--ink);
}
.grow-sub { font-size: 12.5px; color: var(--muted); line-height: 1.55; margin-bottom: 16px; }
.grow-grid {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 12px;
}
.grow-card {
  background: var(--paper); border: 1px solid var(--line); border-radius: 14px; padding: 15px 17px;
  transition: all .2s ease;
}
.grow-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); }
.grow-card-head { display: flex; align-items: center; gap: 8px; margin-bottom: 11px; }
.grow-card-icon { font-size: 17px; line-height: 1; }
.grow-card-title { font-weight: 700; font-size: 14px; color: var(--ink); }
.grow-rows { display: flex; flex-direction: column; gap: 7px; }
.course-row {
  display: flex; align-items: center; justify-content: space-between; gap: 8px;
  background: var(--card); border: 1px solid var(--line); border-radius: 10px;
  padding: 8px 12px; text-decoration: none !important; transition: all .14s ease;
}
.course-row:hover { border-color: var(--accent-2); transform: translateY(-1px); box-shadow: var(--shadow-sm); }
.course-label {
  display: flex; align-items: center; gap: 8px; font-size: 12.5px; color: var(--ink) !important; line-height: 1.35;
}
.course-tag {
  flex-shrink: 0; font-size: 10px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.04em; padding: 3px 10px; border-radius: 999px;
}
.tag-free { background: #e4f1e4; color: #2f6b34; }
.tag-paid { background: var(--accent-soft); color: var(--accent); }
.course-ext { flex-shrink: 0; color: var(--muted); font-size: 13px; }

.grow-support { font-size: 12px; color: var(--muted); margin-top: 14px;
  padding-top: 12px; border-top: 1px dashed var(--line); }
.grow-support a { color: var(--accent) !important; font-weight: 600; text-decoration: none; }
.grow-support a:hover { text-decoration: underline; }

/* ---- SITE FOOTER ---- */
.site-footer { margin-top: 36px; border-top: 1px solid var(--line); }
.site-footer .footer-row {
  display: flex; justify-content: space-between; align-items: center;
  flex-wrap: wrap; gap: 14px; padding: 22px 0 6px;
}
.site-footer .footer-wordmark {
  font-family: 'Newsreader', serif; font-size: 19px; font-weight: 600; color: var(--ink);
}
.site-footer .footer-wordmark .go { color: var(--accent); font-style: italic; }
.site-footer .footer-credits { font-size: 12px; color: var(--muted); line-height: 1.6; max-width: 520px; }
.site-footer .footer-links { font-size: 12.5px; margin-top: 6px; }
.site-footer .footer-links a { color: var(--accent) !important; font-weight: 600; text-decoration: none; }
.site-footer .footer-links a:hover { text-decoration: underline; }
.site-footer .footer-note {
  font-family: 'Newsreader', serif; font-style: italic;
  font-size: 12.5px; color: var(--muted); padding: 6px 0 16px;
}

@media (prefers-reduced-motion: reduce) {
  * { transition: none !important; animation: none !important; }
  /* Looping ambient accents are purely decorative — hide them entirely so
     nothing moves for users who asked for stillness. */
  .smart-match-icon::after, .uni-banner::before { display: none !important; }
}

@media (max-width: 768px) {
  .hero-wrap { padding-top: 18px; }
  .topbar .wordmark { font-size: 26px !important; }
  .hero-wrap h1 { font-size: 32px !important; }
  .hero-sub { font-size: 14px !important; }
  .stat .n { font-size: 22px !important; }
  .stat { padding: 2px 10px !important; }
  .stat .l { font-size: 9px !important; }
  .step-chip { font-size: 12px !important; padding: 7px 13px !important; }
  .step-arrow { display: none; }
  .block-container { padding: 1rem 0.6rem !important; max-width: 100% !important; }
  .uni-banner { padding: 18px 20px !important; }
  .uni-banner .uni-name { font-size: 20px !important; }
  .job-title { font-size: 17px !important; }
  .site-footer .footer-row { flex-direction: column; align-items: flex-start; }
  .smart-match-header { gap: 12px; }
  .smart-match-icon { font-size: 22px; width: 42px; height: 42px; }
  .smart-match-title { font-size: 18px; }
  .smart-match-subtitle { font-size: 12px; }
}
</style>
""", unsafe_allow_html=True)


# ── LOAD DATA ───────────────────────────────────────────────────────────────--
universities = load_universities()

def uni_label(u):
    qs = f"QS #{u['qs']}" if u.get("qs") else "Unranked"
    mark = "✅ " if u.get("mode") == "alumni" else ""
    return f"{mark}{u['name']} · {u['city']} · {qs}"

def sort_key(u):
    is_alumni = u.get("mode") == "alumni"
    if u["id"] == "cdu":
        return (0, 0)
    if is_alumni:
        return (0, u["qs"] if u.get("qs") else 9999)
    return (1, u["qs"] if u.get("qs") else 9999)
universities_sorted = sorted(universities, key=sort_key)


# ── TOP BAR ───────────────────────────────────────────────────────────────────
# Note: this is the APP. The wordmark links back to the landing page so the two
# surfaces feel like one product (see UX review). The hero is intentionally
# lighter than the landing hero to avoid a repetitive "second hero".
n_unis = len(universities_sorted)
n_emps = sum(len(u.get("employers", [])) for u in universities_sorted)
st.markdown(f"""
<div class="topbar">
<a class="wordmark" href="https://gradaroo.com" target="_self">Grad<span class="go">aroo</span></a>
<div class="topbar-links">
<a class="topnav-link" href="https://gradaroo.com" target="_self">Home</a>
<a class="topnav-link" href="/About_Gradaroo" target="_self">About</a>
<a class="kofi-btn" href="{KOFI_URL}" target="_blank" rel="noopener">☕ Support</a>
</div>
</div>
""", unsafe_allow_html=True)

# Compact app-header (NOT a repeat of the landing hero). One line of intent +
# the live stats, then straight into the tool.
st.markdown(f"""
<div class="hero-wrap" style="padding: 18px 0 4px;">
<div class="hero-chip"><span class="live-dot"></span>Live graduate jobs · Australia</div>
<h1 style="font-size:38px; margin-top:14px;">Let's find where <em>you</em> fit.</h1>
<div class="hero-sub">Pick your university below to see where its graduates work — then
browse live openings, or smart-match jobs to your resume.</div>
<div class="stat-strip">
<div class="stat"><div class="n">{n_unis}</div><div class="l">Universities</div></div>
<div class="stat"><div class="n">{n_emps}</div><div class="l">Employers</div></div>
<div class="stat"><div class="n"><em>Live</em></div><div class="l">Updated daily</div></div>
</div>
</div>
""", unsafe_allow_html=True)

if _keys_missing():
    st.warning(
        "**Setup needed.** This app needs Adzuna API keys to fetch jobs.\n\n"
        "Locally: create `.streamlit/secrets.toml` with your keys "
        "(see `secrets.toml.example`).\n\n"
        "Deployed: add them in your app's **Settings → Secrets**."
    )
    st.stop()


# ── CONTROLS ────────────────────────────────────────────────────────────────--
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

# ── SMART MATCH SECTION (single unified card) ────────────────────────────────
resume_cats = []

st.markdown('<div class="section-label">✨ Smart Match · optional</div>', unsafe_allow_html=True)

# Everything below lives in ONE container so the CSS renders it as a single card.
with st.container():
    # Anchor: zero-size element the CSS uses to find "this container".
    st.markdown('<span class="smart-match-root"></span>', unsafe_allow_html=True)

    # Header (in-card, single block — no separate outer box)
    st.markdown("""
<div class="smart-match-header">
<div class="smart-match-icon">📄</div>
<div class="smart-match-header-text">
<div class="smart-match-title">Match jobs to your unique skills</div>
<div class="smart-match-subtitle">Upload your resume → AI reads your skills → we filter jobs to what fits you best.</div>
</div>
</div>
""", unsafe_allow_html=True)

    if PYPDF_OK and GENAI_OK and GEMINI_KEY:
        resume_file = st.file_uploader(
            "Upload your resume (PDF)",
            type=["pdf"],
            label_visibility="collapsed",
            key="smart_resume_upload",
        )

        if resume_file is not None:
            file_sig = (resume_file.name, getattr(resume_file, "size", None))
            if st.session_state.get("resume_sig") != file_sig:
                # st.spinner shows a transient "working" indicator and removes
                # itself automatically when the block exits — no manual placeholder
                # to clear, so there is no stale frame left behind on rerun.
                with st.spinner("Reading your resume and matching your skills…"):
                    st.session_state["resume_result"] = analyse_resume(resume_file, GEMINI_KEY)
                st.session_state["resume_sig"] = file_sig

            result = st.session_state["resume_result"]

            if result["ok"] and result["categories"]:
                resume_cats = result["categories"]
                top = resume_cats[0]
                other_cats = resume_cats[1:]
                summary = result.get("summary", "")

                other_cats_html = "".join(
                    f'<span class="matched-cat-tag">{safe(cat)}</span>' for cat in other_cats
                )

                success_html = f"""
<div class="analysis-success">
<div class="success-header">
<div class="success-icon">✅</div>
<div class="success-title">Skill match complete!</div>
</div>
<div style="font-size: 14px; color: #2f6b34; margin-bottom: 8px; font-weight: 600;">
Your best match:
</div>
<div class="best-match-pill">✨ {safe(top)}</div>
"""
                if summary:
                    success_html += f'<div class="match-summary">💡 {safe(summary)}</div>'
                if other_cats:
                    success_html += f"""
<div style="font-size: 13px; font-weight: 600; color: #2f6b34; margin-top: 4px;">
Also matches:
</div>
<div class="matched-cats-list">{other_cats_html}</div>
"""
                success_html += "</div>"
                st.markdown(success_html, unsafe_allow_html=True)

            elif result["ok"]:
                st.markdown("""
<div class="analysis-warning">
<span class="state-icon">⚠️</span>
<div class="state-text"><strong>Couldn't confidently match your resume.</strong><br>Showing all jobs. Use the category filter below to narrow results.</div>
</div>
""", unsafe_allow_html=True)
            else:
                error_msg = safe(result.get('error', 'Something went wrong.'))
                st.markdown(f"""
<div class="analysis-error">
<span class="state-icon">❌</span>
<div class="state-text"><strong>Oops!</strong><br>{error_msg}</div>
</div>
""", unsafe_allow_html=True)

        # Security note (inside the same card)
        st.markdown("""
<div class="security-note">
<span class="security-icon">🔒</span>
<div>Your resume is processed securely to find your skills. It is never stored, shared, or used for any purpose beyond matching you to jobs. See About for details.</div>
</div>
""", unsafe_allow_html=True)

    else:
        st.markdown("""
<div class="setup-hint">
<span style="font-size: 24px;">🔧</span>
<div class="setup-hint-title">Resume matching needs a quick setup</div>
</div>
<div style="font-size: 14px; color: var(--muted); line-height: 1.6;">
Install the required packages to enable AI-powered resume matching:
<div class="setup-code">pip install pypdf google-genai</div>
</div>
""", unsafe_allow_html=True)


# ── UNIVERSITY BANNER ─────────────────────────────────────────────────────────
qs_html = (f'<div class="qs-badge"><span class="label">QS World 2026</span>'
           f'<span class="num">#{safe(uni["qs"])}</span></div>') if uni.get("qs") else \
          '<div class="qs-badge"><span class="label">QS World 2026</span><span class="num">NR</span></div>'
st.markdown(f"""
<div class="uni-banner">
<div>
<div class="uni-name">{safe(uni['name'])}</div>
<div class="uni-loc">📍 {safe(uni['city'])}, {safe(uni['state'])} · {safe(uni['region'])}</div>
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
    st.caption("These are the state's largest graduate employers. It's a useful starting "
               "point, though not a verified alumni list for this specific university.")


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
            f'{" at " + safe(chosen_employer) if chosen_employer != "All employers" else ""}</span>',
            unsafe_allow_html=True)
st.write("")

if not visible:
    st.info("No jobs match this filter right now. Try removing the interest filter, "
            "or choose **All employers** above.")
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
            st.link_button("Apply ↗", safe_url(j["url"]), use_container_width=True)

# ── GROW YOUR SKILLS ──────────────────────────────────────────────────────────
growth_source = resume_cats if resume_cats else chosen_cats
if growth_source:
    st.write("")
    render_growth_panel(growth_source)

st.markdown(f"""
<div class="site-footer">
<div class="footer-row">
<div>
<div class="footer-wordmark">Grad<span class="go">aroo</span></div>
<div class="footer-credits">Employer data compiled from public sources ·
Job listings via the Adzuna API · QS World University Rankings 2026 ·
"Apply" opens the original posting.</div>
<div class="footer-links">
<a href="https://gradaroo.com" target="_self">Home</a> ·
<a href="/About_Gradaroo" target="_self">About</a> ·
<a href="mailto:harshrastogii@zohomail.com.au">Contact</a>
</div>
</div>
<a class="kofi-btn" href="{KOFI_URL}" target="_blank" rel="noopener">☕ Support on Ko-fi</a>
</div>
<div class="footer-note">Built by Harsh Rastogi. A smarter, honest way to start a graduate job search.</div>
</div>
""", unsafe_allow_html=True)
