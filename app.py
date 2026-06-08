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

# Adzuna keys are required for the core job search.
def _keys_missing():
    return not APP_ID or not APP_KEY


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
                   layout="wide", initial_sidebar_state="expanded")

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

/* ---- HERO ---- */
.hero { padding: 6px 0 2px; border-bottom: 1.5px solid var(--ink); margin-bottom: 4px; }
.hero h1 {
  font-family: 'Newsreader', Georgia, serif; font-weight: 600; font-size: 40px;
  line-height: 1.0; letter-spacing: -0.02em; margin: 0; color: var(--ink);
}
.hero h1 .go { color: var(--accent); font-style: italic; }
.hero .sub {
  font-size: 14px; color: var(--muted); margin-top: 8px; font-weight: 400;
}

/* ---- UNIVERSITY BANNER ---- */
.uni-banner {
  background: var(--ink); border-radius: 14px;
  padding: 20px 24px; margin: 16px 0 6px;
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
  padding: 18px 20px; margin-bottom: 12px; transition: all .16s ease;
}
.job-card:hover { border-color: var(--accent); transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(179,67,26,.10); }
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
  font-size: 11px; text-transform: uppercase; letter-spacing: 0.15em;
  color: var(--muted); font-weight: 700; margin: 14px 0 4px;
}
.count-big { font-family: 'Newsreader', serif; font-size: 32px; font-weight: 600; color: var(--ink); }

/* ---- LINK BUTTON ---- */
.stLinkButton a {
  background: var(--ink) !important; color: #ffffff !important;
  border: none !important; border-radius: 8px !important; font-weight: 600 !important;
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


# ── HERO ────────────────────────────────────────────────────────────────────--
st.markdown("""
<div class="hero">
  <h1>WhereGrads<span class="go">Go</span></h1>
  <div class="sub">Find live jobs at the organisations your university's graduates actually work for.</div>
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
with st.expander("ℹ️  About WhereGradsGo — how it works & data honesty"):
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

*A student project · QS rankings from QS World University Rankings 2026.*
""")


# ── SIDEBAR ─────────────────────────────────────────────────────────────────--
with st.sidebar:
    st.markdown("### 🎓 Search")
    labels = [uni_label(u) for u in universities_sorted]
    idx = st.selectbox("University", range(len(labels)),
                       format_func=lambda i: labels[i])
    uni = universities_sorted[idx]

    mode = uni.get("mode", "")
    has_employers = len(uni["employers"]) > 0
    if has_employers:
        emp_label = "Employer" if mode == "alumni" else "Major employer"
        employer_options = ["All employers"] + [e["name"] for e in uni["employers"]]
        chosen_employer = st.selectbox(emp_label, employer_options)
    else:
        chosen_employer = None

    st.markdown("---")
    st.markdown(f"**Region:** {uni['region']}")
    st.markdown(f"**Employers on file:** {len(uni['employers'])}")
    if mode == "alumni":
        st.caption("✅ Curated list of where this university's graduates commonly work, "
                   "compiled from public sources.")
    elif mode == "metro":
        st.caption("ℹ️ This shows the largest graduate employers in the state "
                   "(not a verified alumni list). Curated alumni lists exist for "
                   "regional universities — look for ✅ ones.")

    # ── Resume upload (AI-powered) ──
    st.markdown("---")
    st.markdown("### 📄 Smart match")
    resume_cats = []
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
                with st.expander("All matched areas"):
                    for c in resume_cats:
                        st.markdown(f"• {c}")
            elif result["ok"]:
                st.warning("AI couldn't confidently match your resume. "
                           "Showing all jobs — use the filter above.")
            else:
                st.error(result.get("error", "Something went wrong."))
        st.caption("⚠️ Resumes are analysed by Google's free-tier AI.")
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

st.markdown("---")
st.caption("Employer data compiled from public sources · Job listings via the Adzuna API · "
           "QS World University Rankings 2026 · 'Apply' opens the original posting.")
