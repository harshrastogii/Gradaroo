"use client";

import { useState, useRef } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Where the rest of Gradaroo lives. Override per-environment if the domains change.
const SITE = process.env.NEXT_PUBLIC_SITE_URL || "https://gradaroo.com";
const APP = "https://gradaroo.com/jobs";

export default function Page() {
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<"idle" | "working" | "done" | "error">("idle");
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function pick(f: File | null) {
    setError("");
    setStatus("idle");
    if (!f) return;
    if (f.type !== "application/pdf") { setError("Please choose a PDF."); return; }
    if (f.size > 5 * 1024 * 1024) { setError("That PDF is too large (max 5 MB)."); return; }
    setFile(f);
  }

  async function convert() {
    if (!file) return;
    setStatus("working");
    setError("");
    try {
      const body = new FormData();
      body.append("file", file);
      const res = await fetch(`${API}/convert`, { method: "POST", body });
      if (!res.ok) {
        const msg = await res.json().catch(() => null);
        throw new Error(msg?.detail || "Conversion failed. Please try again.");
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "resume-australian-format.docx";
      a.click();
      URL.revokeObjectURL(url);
      setStatus("done");
    } catch (e: any) {
      setError(e.message || "Something went wrong.");
      setStatus("error");
    }
  }

  return (
    <>
      <style>{css}</style>

      {/* ── Top nav: same wordmark + links as the landing page ── */}
      <header className="topbar-wrap">
        <div className="wrap topbar">
          <a className="wordmark" href={SITE}>Grad<span className="go">aroo</span></a>
          <nav className="topnav">
            <a href={APP}>Find jobs</a>
            <a href={`${SITE}/about`}>About</a>
            <a className="nav-active" href="#">Resume converter</a>
          </nav>
        </div>
      </header>

      <main className="wrap">
        {/* ── Hero ── */}
        <section className="hero">
          <span className="chip"><span className="dot" />Australian resume standard</span>
          <h1>Turn your resume into the <em>Australian</em> format.</h1>
          <p className="lede">
            Upload your current resume and Gradaroo reformats it to the Australian
            standard — clean, ATS-safe, and recruiter-ready. You get an editable
            Word draft back. Nothing is stored.
          </p>
        </section>

        {/* ── Converter card ── */}
        <section className="card">
          <div
            className={`drop${dragging ? " dragging" : ""}${file ? " has-file" : ""}`}
            onClick={() => inputRef.current?.click()}
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => { e.preventDefault(); setDragging(false); pick(e.dataTransfer.files?.[0] || null); }}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") inputRef.current?.click(); }}
          >
            <input
              ref={inputRef}
              type="file"
              accept="application/pdf"
              style={{ display: "none" }}
              onChange={(e) => pick(e.target.files?.[0] || null)}
            />
            {file ? (
              <div className="file-chip">
                <span className="file-ico">📄</span>
                <span className="file-name">{file.name}</span>
                <span className="file-swap">Click to change</span>
              </div>
            ) : (
              <div className="drop-empty">
                <span className="drop-ico">⤓</span>
                <span className="drop-title">Drag your PDF here</span>
                <span className="drop-hint">or click to browse — max 5 MB</span>
              </div>
            )}
          </div>

          <button
            className="btn"
            onClick={convert}
            disabled={!file || status === "working"}
          >
            {status === "working" ? "Converting…" : "Convert to Australian format"}
          </button>

          {status === "done" && (
            <p className="msg ok">✅ Done — your draft downloaded. Open it in Word for final edits.</p>
          )}
          {error && <p className="msg err">⚠️ {error}</p>}

          <p className="note">
            This produces a professional draft, not a finished resume. Review and
            edit before sending. We never invent experience — only what's in your file.
          </p>
        </section>

        {/* ── Reassurance row ── */}
        <section className="trust">
          <div className="trust-item">
            <span className="trust-ico">🔒</span>
            <div><b>Not stored</b><span>Your file is processed, then discarded.</span></div>
          </div>
          <div className="trust-item">
            <span className="trust-ico">🇦🇺</span>
            <div><b>AU conventions</b><span>Strips photo, DOB &amp; age; AU spelling.</span></div>
          </div>
          <div className="trust-item">
            <span className="trust-ico">✍️</span>
            <div><b>Editable draft</b><span>A Word file you finish in your own words.</span></div>
          </div>
        </section>
      </main>

      <footer className="wrap site-foot">
        <a className="foot-wordmark" href={SITE}>Grad<span className="go">aroo</span></a>
        <span className="foot-note">A smarter, honest start to the Australian graduate job search.</span>
      </footer>
    </>
  );
}

const css = `
@import url('https://fonts.googleapis.com/css2?family=Libre+Franklin:wght@400;500;600;700;800&family=Newsreader:opsz,wght@6..72,400;6..72,500;6..72,600&display=swap');

:root {
  --ink: #1c1917;
  --paper: #fff7ed;
  --paper-grad: linear-gradient(180deg, #fff7ed 0%, #faf6f0 50%, #fff7ed 100%);
  --card: #ffffff;
  --accent-dark: #7a240a;
  --accent: #bc4514;
  --accent-light: #e8742c;
  --grad: linear-gradient(135deg, #7a240a 0%, #bc4514 35%, #e8742c 100%);
  --text-grad: linear-gradient(135deg, #9a3412 0%, #bc4514 100%);
  --line: #ede0d0;
  --muted: #6a5f52;
  --muted-deep: #4a3f32;
  --shadow-soft: 0 2px 10px rgba(122,36,10,.04), 0 12px 40px rgba(122,36,10,.08);
  --shadow-hover: 0 8px 24px rgba(122,36,10,.10), 0 24px 60px rgba(122,36,10,.15);
  --ease: cubic-bezier(0.4, 0, 0.2, 1);
}

* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  background: var(--paper-grad);
  background-image: radial-gradient(circle at 20px 20px, rgba(188,69,20,.04) 1px, transparent 0);
  background-size: 40px 40px;
  color: var(--ink);
  font-family: 'Libre Franklin', -apple-system, sans-serif;
  line-height: 1.6;
}
.wrap { max-width: 760px; margin: 0 auto; padding: 0 24px; }
a { color: var(--accent); text-decoration: none; transition: color .16s var(--ease); }
@keyframes rise { from { opacity: 0; transform: translateY(16px); } to { opacity: 1; transform: none; } }

/* ── NAV ── */
.topbar-wrap {
  position: sticky; top: 0; z-index: 50;
  background: rgba(255,247,237,.82); backdrop-filter: blur(16px);
  border-bottom: 1px solid var(--line);
}
.topbar { display: flex; justify-content: space-between; align-items: center; gap: 24px; padding: 16px 24px; }
.wordmark { font-family: 'Newsreader', Georgia, serif; font-size: 28px; font-weight: 600; letter-spacing: -.02em; color: var(--ink); }
.wordmark .go { background: var(--text-grad); -webkit-background-clip: text; background-clip: text; color: transparent; font-style: italic; padding-right: 6px; }
.topnav { display: flex; align-items: center; gap: 22px; }
.topnav a { color: var(--ink); font-size: 14px; font-weight: 600; }
.topnav a:hover { color: var(--accent); }
.topnav a.nav-active {
  background: var(--grad); color: #fff; padding: 8px 16px; border-radius: 999px;
  box-shadow: 0 4px 14px rgba(188,69,20,.28);
}
.topnav a.nav-active:hover { color: #fff; }

/* ── HERO ── */
.hero { text-align: center; padding: 54px 0 22px; animation: rise .6s var(--ease) both; }
.chip {
  display: inline-flex; align-items: center; gap: 9px;
  background: rgba(255,255,255,.9); border: 1px solid var(--line); box-shadow: var(--shadow-soft);
  border-radius: 999px; padding: 7px 16px; font-size: 12px; font-weight: 600;
  letter-spacing: .05em; color: var(--muted); text-transform: uppercase;
}
.chip .dot { width: 9px; height: 9px; border-radius: 50%; background: var(--grad); box-shadow: 0 0 10px rgba(232,116,44,.6); animation: pulse 2s infinite; }
@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: .5; } }
.hero h1 {
  font-family: 'Newsreader', Georgia, serif; font-weight: 500;
  font-size: clamp(2.1rem, 5vw, 3.4rem); line-height: 1.18; letter-spacing: -.025em;
  margin: 20px auto 0; max-width: 600px;
}
.hero h1 em { font-style: italic; background: var(--text-grad); -webkit-background-clip: text; background-clip: text; color: transparent; padding-right: 6px; }
.lede { font-size: clamp(1rem, 2vw, 1.12rem); color: var(--muted-deep); max-width: 560px; margin: 16px auto 0; line-height: 1.7; }

/* ── CARD ── */
.card {
  background: var(--card); border: 1px solid var(--line); border-radius: 22px;
  box-shadow: var(--shadow-soft); padding: 28px; margin-top: 10px;
  animation: rise .6s var(--ease) .08s both;
}
.drop {
  border: 2px dashed var(--accent-light); border-radius: 16px;
  background: linear-gradient(135deg, #fff5ed 0%, #f9ece2 100%);
  padding: 38px 24px; text-align: center; cursor: pointer;
  transition: all .2s var(--ease); margin-bottom: 16px;
}
.drop:hover, .drop.dragging { border-color: var(--accent); background: #f9ece2; transform: translateY(-1px); }
.drop.has-file { border-style: solid; border-color: var(--accent); }
.drop-empty { display: flex; flex-direction: column; align-items: center; gap: 6px; }
.drop-ico { font-size: 30px; color: var(--accent); line-height: 1; }
.drop-title { font-weight: 700; font-size: 16px; color: var(--ink); }
.drop-hint { font-size: 13px; color: var(--muted); }
.file-chip { display: flex; flex-direction: column; align-items: center; gap: 4px; }
.file-ico { font-size: 26px; }
.file-name { font-weight: 700; font-size: 15px; color: var(--ink); word-break: break-all; }
.file-swap { font-size: 12px; color: var(--accent); font-weight: 600; }

.btn {
  width: 100%; padding: 14px 22px; border: none; border-radius: 999px;
  background: var(--grad); color: #fff; font-weight: 600; font-size: 15px;
  font-family: inherit; cursor: pointer; box-shadow: 0 4px 16px rgba(188,69,20,.3);
  transition: transform .2s var(--ease), box-shadow .2s var(--ease), opacity .2s var(--ease);
}
.btn:hover:not(:disabled) { transform: translateY(-2px) scale(1.01); box-shadow: 0 8px 28px rgba(188,69,20,.45); }
.btn:active:not(:disabled) { transform: translateY(0) scale(.99); }
.btn:disabled { opacity: .55; cursor: not-allowed; }

.msg { font-size: 14px; margin: 14px 0 0; padding: 12px 16px; border-radius: 12px; }
.msg.ok { color: #2f6b34; background: #f0f7f0; border: 1px solid #c6e4c6; }
.msg.err { color: #b3261e; background: #fff0f0; border: 1px solid #e8b4b4; }
.note { font-size: 12.5px; color: var(--muted); margin: 16px 0 0; line-height: 1.6; }

/* ── TRUST ROW ── */
.trust { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 18px 0 0; animation: rise .6s var(--ease) .16s both; }
.trust-item {
  background: rgba(255,255,255,.7); border: 1px solid var(--line); border-radius: 14px;
  padding: 14px 16px; display: flex; gap: 11px; align-items: flex-start;
}
.trust-ico { font-size: 18px; line-height: 1.3; flex-shrink: 0; }
.trust-item b { display: block; font-size: 13.5px; color: var(--ink); }
.trust-item span { display: block; font-size: 12px; color: var(--muted); line-height: 1.45; margin-top: 2px; }

/* ── FOOTER ── */
.site-foot { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; margin-top: 40px; padding-top: 24px; padding-bottom: 32px; border-top: 1px solid var(--line); }
.foot-wordmark { font-family: 'Newsreader', serif; font-size: 19px; font-weight: 600; color: var(--ink); }
.foot-wordmark .go { color: var(--accent); font-style: italic; }
.foot-note { font-family: 'Newsreader', serif; font-style: italic; font-size: 13px; color: var(--muted); }

@media (max-width: 640px) {
  .topnav { gap: 12px; }
  .topnav a { font-size: 13px; }
  .topnav a:not(.nav-active) { display: none; }
  .trust { grid-template-columns: 1fr; }
  .site-foot { flex-direction: column; align-items: flex-start; }
}

@media (prefers-reduced-motion: reduce) {
  * { animation: none !important; transition: none !important; scroll-behavior: auto !important; }
}
`;
