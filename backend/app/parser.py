"""Resume parsing: arbitrary uploaded resume text -> structured JSON in our
Australian-template shape. The prompt is the moat — it encodes AU conventions
and forbids fabrication."""

import json
import time
from google import genai

AU_SCHEMA = {
    "name": "str",
    "tagline": "str (role focus | 3-5 keywords; '' if unclear)",
    "contact": {"location": "str", "phone": "str", "email": "str", "links": "str"},
    "profile": "str (3-4 sentences, third person, no 'I')",
    "skills": [{"label": "str", "detail": "str"}],
    "projects": [{"org": "str", "dates": "str", "role": "str",
                  "location": "str", "bullets": ["str"]}],
    "experience": [{"org": "str", "dates": "str", "role": "str",
                    "location": "str", "bullets": ["str"]}],
    "education": [{"left": "str", "dates": "str", "sub": "str"}],
    "certifications": "str (' · '-separated single line)",
}

PROMPT = """You convert a resume into a clean Australian-standard structure.

AUSTRALIAN CONVENTIONS (apply these):
- Remove any photo reference, date of birth, age, marital status, gender, nationality. These do NOT belong on an Australian resume.
- Reverse-chronological (most recent first) for experience, projects, education.
- Australian spelling (organise, optimise, programme->program where appropriate, centre).
- Phone in +61 format if a number is present and clearly Australian; otherwise leave as given.
- Keep "References: available on request" handled by the template — do not include it.
- Profile: 3-4 sentences, third person, NO first-person "I".

CRITICAL — NEVER FABRICATE:
- Only use information present in the source resume.
- Do NOT invent skills, employers, dates, metrics, or achievements.
- You may reword, reorder, and tighten. You may NOT add facts that are not there.
- If a field is missing, use "" (empty string) or omit the list item. Never guess.

OUTPUT: Return ONLY valid JSON (no markdown, no prose) matching exactly this shape:
{schema}

Notes:
- "skills" = the key-skills/strengths block as label+detail lines (e.g. label "Communication", detail "Clear phone manner; ...").
- If a skill in the source is only a bare keyword with no real description (e.g. "Teamwork", "Time Management"), set its "detail" to "" (empty). Do NOT invent or pad a description. Bare keywords will be grouped on one line by the template.
- "projects" is optional; include only if the resume has a distinct projects section, else return [].
- "tagline" = the short role-focus line under the name; "" if none.
- "certifications" = licences/certs/eligibility joined with ' · ' on one line.

RESUME TEXT:
{resume}
"""


def parse_resume(resume_text: str, api_key: str) -> dict:
    client = genai.Client(api_key=api_key)
    prompt = PROMPT.format(schema=json.dumps(AU_SCHEMA, indent=2),
                           resume=resume_text[:14000])
    last_err = ""
    for attempt in range(4):
        try:
            resp = client.models.generate_content(
                model="gemini-2.5-flash", contents=prompt)
            raw = (resp.text or "").replace("```json", "").replace("```", "").strip()
            data = json.loads(raw)
            return _normalise(data)
        except json.JSONDecodeError as e:
            last_err = f"parse: {e}"
        except Exception as e:
            last_err = str(e)
            if any(c in last_err for c in ("503", "429", "UNAVAILABLE")):
                time.sleep(2 * (attempt + 1))
                continue
            break
    raise RuntimeError(f"AI parsing failed: {last_err}")


def _normalise(d: dict) -> dict:
    """Defensive defaults so the renderer never crashes on a missing key."""
    d.setdefault("name", "")
    d.setdefault("tagline", "")
    c = d.get("contact") or {}
    d["contact"] = {k: c.get(k, "") for k in ("location", "phone", "email", "links")}
    d.setdefault("profile", "")
    for k in ("skills", "projects", "experience", "education"):
        if not isinstance(d.get(k), list):
            d[k] = []
    d.setdefault("certifications", "")
    return d
