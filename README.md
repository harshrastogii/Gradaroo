# 🎓 Gradaroo

**Find live jobs at the organisations your university's graduates actually work for.**

🔗 **Live:** [gradaroo.com](https://gradaroo.com) · **App:** [app.gradaroo.com](https://app.gradaroo.com)

---

## The idea

Most job boards make you search a giant pile of listings with no starting point. Gradaroo flips that around: the employers who hire a lot of a university's graduates tend to keep hiring them, so it makes sense to start your search *there*.

Pick your university, see the organisations its graduates commonly work for, and browse live job openings at those employers — filtered by your area of interest, or matched to your skills by AI from your resume.

## What it does

- **Pick your university** — 40 Australian universities, sorted by QS World Ranking.
- **See its key employers** — either a curated alumni-employer list or the state's largest graduate employers (clearly labelled — see *Data honesty* below).
- **Browse live jobs** at those employers, pulled in real time from the Adzuna job API.
- **Filter by area of interest** using job categories.
- **Smart match (AI)** — upload your resume (PDF) and Google's Gemini reads your actual skills, then auto-matches you to relevant job categories.
- **Grow your skills** — for your matched areas, Gradaroo suggests free and paid courses to help close any gaps.
- **Apply** — links straight to the original job posting.

## Architecture

Gradaroo runs as two services under one brand, which is what makes it both fast to find and fully interactive:

- **`gradaroo.com`** — a static landing page (plain HTML). It loads instantly, is fully crawlable by search engines, and carries the SEO metadata, Open Graph tags, and structured data. This is the front door.
- **`app.gradaroo.com`** — the Streamlit app: the interactive job-search tool. The landing page's "Find jobs" buttons link here.

A Streamlit app alone serves an almost-empty HTML shell to search crawlers (the content is painted in by JavaScript afterwards), so it ranks poorly. Putting a static landing page in front solves that while keeping the Python app exactly as-is — the same split larger products use (a marketing site in front of a web app).

## Data honesty

This was a deliberate design priority. The app never pretends data is something it isn't:

- **✅ Curated universities** (Charles Darwin, Tasmania, James Cook, Charles Sturt, University of New England, CQUniversity, Federation) show employer lists compiled from public, regional employment sources — a genuine reflection of where graduates commonly work.
- **Other universities** show the *largest graduate employers in the state* — a useful starting point, but not a verified alumni list for that specific university. This is labelled clearly in the app.
- **No scraping.** The app does not scrape LinkedIn or any site's private data. Job listings come from a proper job API; employer lists are curated from public information.
- **Resume privacy.** Uploaded resumes are sent to Google's Gemini (free tier) to identify skills, and are not stored. The app notes this so users can decide what to share.

## Tech stack

- **App:** [Streamlit](https://streamlit.io) (multipage: job search + About)
- **Landing page:** static HTML/CSS, with Open Graph tags, JSON-LD structured data, sitemap, and robots.txt
- **Job data:** [Adzuna API](https://developer.adzuna.com)
- **Resume understanding:** [Google Gemini](https://ai.google.dev) (`gemini-2.5-flash`)
- **PDF parsing:** pypdf
- **Hosting:** [Render](https://render.com) — one web service for the app, one static site for the landing page

## Running it locally

```bash
# 1. clone the repo
git clone https://github.com/harshrastogii/Gradaroo.git
cd Gradaroo

# 2. install dependencies
pip install -r requirements.txt

# 3. add your API keys
# create .streamlit/secrets.toml with:
#   ADZUNA_APP_ID = "your_id"
#   ADZUNA_APP_KEY = "your_key"
#   GEMINI_API_KEY = "your_key"
# (see .streamlit/secrets.toml.example)

# 4. run
streamlit run app.py
```

You'll need free API keys from [Adzuna](https://developer.adzuna.com/signup) and [Google AI Studio](https://aistudio.google.com/apikey).

The job search runs with just the two Adzuna keys. The Gemini key is optional — without it, everything works except the resume smart-match.

## Deploying on Render

The repo includes a `render.yaml` blueprint for the app. Render reads it, installs from `requirements.txt`, and starts the app with:

```bash
streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true
```

Add `ADZUNA_APP_ID`, `ADZUNA_APP_KEY`, and `GEMINI_API_KEY` as environment variables in the Render dashboard (**Settings → Environment**). The app reads secrets from either environment variables (Render) or `.streamlit/secrets.toml` (local), so the same code runs on both.

The landing page is deployed as a separate Render **Static Site** with publish directory `landing/` (no build command needed). The app holds the `app.gradaroo.com` custom domain; the static site holds `gradaroo.com` and `www.gradaroo.com`.

## Project structure

```
Gradaroo/
├── app.py                      # the Streamlit app (job search — home page)
├── employers.json              # university → employer dataset
├── requirements.txt            # Python dependencies
├── render.yaml                 # Render deployment blueprint (the app)
├── .gitignore
├── pages/
│   └── About_Gradaroo.py       # About page (the story, how it works, data handling)
├── landing/                    # static SEO landing page (served at gradaroo.com)
│   ├── index.html
│   ├── og-image.png            # Open Graph share image (link previews)
│   ├── robots.txt
│   └── sitemap.xml
└── .streamlit/
    ├── config.toml             # theme + UI config
    └── secrets.toml.example    # API key template
```

## Notes & limitations

- Job locations are shown as provided by the data source and may be approximate for regional areas.
- The Gemini free tier has rate limits and may occasionally be busy; the app retries automatically.
- Employer lists for non-curated universities are state-level approximations, not verified alumni data.

## About

Built by Harsh Rastogi as a project exploring a smarter, ethical approach to graduate job search. QS rankings from the QS World University Rankings 2026.
