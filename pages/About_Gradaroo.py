"""
About Gradaroo. The story, how it works, and how we handle data.
This is page 2 of the multipage app. The home page (job search) is app.py.
"""

import streamlit as st

st.set_page_config(page_title="About Gradaroo", page_icon="🎓",
                   layout="centered", initial_sidebar_state="collapsed")

# Hide Streamlit's auto-generated page nav and the top-right toolbar so the
# page reads as a clean website, matching the home page. The branded boot cover
# below is CSS-only (pseudo-elements) — no JS, no DOM manipulation — so it cannot
# crash Streamlit's React render cycle.
st.markdown("""
<style>
[data-testid="stSidebarNav"] { display: none; }
[data-testid="stSidebar"] { display: none; }
[data-testid="stSidebarCollapsedControl"] { display: none; }
[data-testid="collapsedControl"] { display: none; }
[data-testid="stToolbar"] { display: none; }
[data-testid="stStatusWidget"] { display: none; }
[data-testid="stDecoration"] { display: none; }
#MainMenu { display: none; }
header { display: none; }

/* --- Branded boot cover (CSS-only; same as home page) --- */
@keyframes gr-boot-fade {
  0%   { opacity: 1; visibility: visible; }
  82%  { opacity: 1; visibility: visible; }
  100% { opacity: 0; visibility: hidden; }
}
@keyframes gr-boot-spin { to { transform: rotate(360deg); } }
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

# Shared styling (kept light here; the home page carries the full theme).
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Libre+Franklin:wght@400;500;600;700;800&family=Newsreader:opsz,wght@6..72,400;6..72,500;6..72,600&display=swap');
:root { --ink:#1c1917; --paper:#faf6f0; --accent:#bc4514; --accent-2:#e8742c;
  --grad: linear-gradient(135deg, #bc4514 0%, #e8742c 100%);
  --muted:#756c5f; --line:#ece3d6; }
html, body, [data-testid="stAppViewContainer"] { background: var(--paper); }
[data-testid="stAppViewContainer"], .stMarkdown, p, li { font-family:'Libre Franklin',sans-serif; color:var(--ink); }
.block-container { max-width: 760px; padding-top: 2.2rem; }
.about-eyebrow { font-size:11px; letter-spacing:.16em; text-transform:uppercase; color:var(--accent); font-weight:700; }
.about-title { font-family:'Newsreader',serif; font-size:46px; font-weight:500; letter-spacing:-.02em; line-height:1.05; margin:6px 0 0; }
.about-title em { font-style:italic; color:var(--accent); }
.about-lede { font-size:17px; color:var(--muted); line-height:1.6; margin-top:14px; }
.about-h { font-family:'Newsreader',serif; font-size:25px; font-weight:600; margin:34px 0 6px; }
.about-card { background:#fff; border:1px solid var(--line); border-radius:16px; padding:18px 22px; margin-top:12px;
  box-shadow:0 1px 2px rgba(28,25,23,.05), 0 4px 14px rgba(28,25,23,.06); }
.honesty-good { border-left:3px solid #2f6b34; }
.honesty-care { border-left:3px solid var(--accent); }
.backlink a { color:var(--accent) !important; font-weight:600; text-decoration:none; }

/* ---- CONTACT SECTION ---- */
.contact-card {
  background: linear-gradient(135deg, #1c1917 0%, #33241a 100%);
  border-radius: 18px; padding: 26px 28px; margin-top: 14px;
  box-shadow: 0 4px 10px rgba(28,25,23,.07), 0 16px 36px rgba(28,25,23,.11);
  display: flex; align-items: center; justify-content: space-between;
  flex-wrap: wrap; gap: 18px;
}
.contact-card .contact-copy { flex: 1; min-width: 240px; }
.contact-card .contact-kicker {
  font-size: 10.5px; text-transform: uppercase; letter-spacing: .15em;
  color: var(--accent-2); font-weight: 700;
}
.contact-card .contact-head {
  font-family: 'Newsreader', serif; font-size: 22px; font-weight: 600;
  color: #ffffff; margin-top: 4px;
}
.contact-card .contact-sub { color: #c9c0b4; font-size: 13.5px; margin-top: 6px; line-height: 1.55; }
.contact-btn {
  display: inline-flex; align-items: center; gap: 9px; white-space: nowrap;
  background: var(--grad); color: #ffffff !important; text-decoration: none !important;
  border-radius: 999px; padding: 12px 22px; font-size: 14px; font-weight: 600;
  box-shadow: 0 8px 22px rgba(188,69,20,.40); transition: transform .16s ease, box-shadow .16s ease;
}
.contact-btn:hover { transform: translateY(-2px); box-shadow: 0 12px 28px rgba(188,69,20,.5); }
.contact-meta { font-size: 12.5px; color: var(--muted); margin-top: 12px; }
.contact-meta a { color: var(--accent) !important; font-weight: 600; text-decoration: none; }
.contact-meta a:hover { text-decoration: underline; }

@media (max-width: 640px) {
  .about-title { font-size: 34px; }
  .contact-card { flex-direction: column; align-items: flex-start; text-align: left; }
}
</style>
""", unsafe_allow_html=True)

# Simple back links to the job search and the landing page.
st.markdown('<div class="backlink">', unsafe_allow_html=True)
st.page_link("app.py", label="← Back to job search")
st.markdown('</div>', unsafe_allow_html=True)

st.markdown("""
<div class="about-eyebrow">About Gradaroo</div>
<div class="about-title">A smarter place to <em>start</em> your search.</div>
<div class="about-lede">Most job boards hand you a giant pile of listings and no idea where to begin.
Gradaroo starts from a simple truth: the organisations that hire a lot of a university's
graduates tend to keep hiring them. So that's where your search should start.</div>
""", unsafe_allow_html=True)

st.markdown('<div class="about-h">The story</div>', unsafe_allow_html=True)
st.markdown("""
Gradaroo began as a project exploring a smarter, more honest approach to the graduate
job hunt in Australia. Instead of asking you to compete in an endless search box, it
turns the problem around: pick your university, see the employers its graduates actually
work for, and browse live openings at those places first. It's the head start that
careers offices and word-of-mouth give some students, made available to everyone.
""")

st.markdown('<div class="about-h">How it works</div>', unsafe_allow_html=True)
st.markdown("""
1. **Pick your university.** 40 Australian universities, sorted by world ranking.
2. **See where its grads work.** A curated employer list, or the state's largest
   graduate employers (always clearly labelled).
3. **Browse and apply.** Live openings at those employers, with Apply linking straight
   to the original posting.
4. **Smart match.** Upload your resume and Gradaroo reads your skills, then matches
   you to the right job areas.
5. **Grow your skills.** For the areas you match, Gradaroo suggests free and paid
   courses so you can close any gaps.
""")

st.markdown('<div class="about-h">Being honest about the data</div>', unsafe_allow_html=True)
st.markdown("""
<div class="about-card honesty-good">
<b>✅ Curated universities</b> (Charles Darwin, Tasmania, James Cook, Charles Sturt,
University of New England, CQUniversity, Federation) show employer lists compiled from
public, regional employment sources, a genuine reflection of where graduates commonly work.
</div>
<div class="about-card honesty-care">
<b>Other universities</b> show the <i>largest graduate employers in the state</i>: a useful
starting point, but not a verified alumni list for that specific university. We label this
clearly in the app so you always know what you're looking at.
</div>
<div class="about-card">
<b>No scraping.</b> We don't scrape LinkedIn or any site's private data. Job listings come
from a proper jobs API; employer lists are curated from public information.
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="about-h">How we handle your resume</div>', unsafe_allow_html=True)
st.markdown("""
Smart match is optional, and the app works fully without it. If you do upload a resume, its
text is read by a third-party AI service (Google's Gemini, free tier) to identify your
skills and match them to job areas. We don't store your resume, and nothing is shared
beyond that matching step. As a rule of thumb: don't upload anything you wouldn't be
comfortable sharing with a third-party AI service.
""")

# ── CONTACT US ────────────────────────────────────────────────────────────────
st.markdown('<div class="about-h">Contact us</div>', unsafe_allow_html=True)
st.markdown("""
<div class="contact-card">
  <div class="contact-copy">
    <div class="contact-kicker">Get in touch</div>
    <div class="contact-head">Questions, feedback or a correction?</div>
    <div class="contact-sub">Gradaroo is built and maintained by one person. If you've spotted
      an issue, want a university added, or just want to say hello, I'd genuinely like to hear from you.</div>
  </div>
  <a class="contact-btn" href="mailto:harshrastogii@zohomail.com.au">✉️ Email us</a>
</div>
<div class="contact-meta">
  Prefer to copy it? <a href="mailto:harshrastogii@zohomail.com.au">harshrastogii@zohomail.com.au</a> ·
  We aim to reply within a few days.
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div style="margin-top:30px; padding-top:16px; border-top:1px solid var(--line);
font-size:12.5px; color:var(--muted); font-family:'Newsreader',serif; font-style:italic;">
Built by Harsh Rastogi. Job listings via the Adzuna API. QS rankings from the
QS World University Rankings 2026.
</div>
""", unsafe_allow_html=True)
