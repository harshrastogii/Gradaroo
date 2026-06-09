# 🎓 WhereGradsGo

**Find live jobs at the organisations your university's graduates actually work for.**

🔗 **Live app:** [wheregradsgo.streamlit.app](https://wheregradsgo.streamlit.app)

---

## The idea

Most job boards make you search a giant pile of listings with no starting point. WhereGradsGo flips that around: the employers who hire a lot of a university's graduates tend to keep hiring them, so it makes sense to start your search *there*.

Pick your university, see the organisations its graduates commonly work for, and browse live job openings at those employers — filtered by your area of interest, or matched to your skills by AI from your resume.

## What it does

- **Pick your university** — 40 Australian universities, sorted by QS World Ranking.
- **See its key employers** — either a curated alumni-employer list or the state's largest graduate employers (clearly labelled — see *Data honesty* below).
- **Browse live jobs** at those employers, pulled in real time from the Adzuna job API.
- **Filter by area of interest** using job categories.
- **Smart match (AI)** — upload your resume (PDF) and Google's Gemini reads your actual skills, then auto-matches you to relevant job categories.
- **Apply** — links straight to the original job posting.

## Data honesty

This was a deliberate design priority. The app never pretends data is something it isn't:

- **✅ Curated universities** (Charles Darwin, Tasmania, James Cook, Charles Sturt, University of New England, CQUniversity, Federation) show employer lists compiled from public, regional employment sources — a genuine reflection of where graduates commonly work.
- **Other universities** show the *largest graduate employers in the state* — a useful starting point, but not a verified alumni list for that specific university. This is labelled clearly in the app.
- **No scraping.** The app does not scrape LinkedIn or any site's private data. Job listings come from a proper job API; employer lists are curated from public information.
- **Resume privacy.** Uploaded resumes are sent to Google's Gemini (free tier) to identify skills. The app notes this so users can decide what to share.

## Tech stack

- **Frontend & app:** [Streamlit](https://streamlit.io)
- **Job data:** [Adzuna API](https://developer.adzuna.com)
- **Resume understanding:** [Google Gemini](https://ai.google.dev) (`gemini-2.5-flash`)
- **PDF parsing:** pypdf
- **Hosting:** Streamlit Community Cloud

## Running it locally

```bash
# 1. clone the repo
git clone https://github.com/harshrastogii/WhereGradsGo.git
cd WhereGradsGo

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

## Project structure

```
WhereGradsGo/
├── app.py                      # the Streamlit app
├── employers.json              # university → employer dataset
├── requirements.txt            # Python dependencies
├── .gitignore
└── .streamlit/
    ├── config.toml             # theme
    └── secrets.toml.example    # API key template
```

## Notes & limitations

- Job locations are shown as provided by the data source and may be approximate for regional areas.
- The Gemini free tier has rate limits and may occasionally be busy; the app retries automatically.
- Employer lists for non-curated universities are state-level approximations, not verified alumni data.

## About

Built by Harsh Rastogi as a project exploring a smarter, ethical approach to graduate job search. QS rankings from the QS World University Rankings 2026.
