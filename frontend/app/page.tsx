"use client";

import { useState, useRef } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Page() {
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<"idle" | "working" | "done" | "error">("idle");
  const [error, setError] = useState("");
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
    <main style={s.main}>
      <div style={s.card}>
        <h1 style={s.h1}>Australian Resume Converter</h1>
        <p style={s.sub}>
          Upload your resume (PDF). We reformat it to the Australian standard and
          give you an editable draft. Your file isn’t stored.
        </p>

        <div
          style={{ ...s.drop, borderColor: file ? "#bc4514" : "#e8742c" }}
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => { e.preventDefault(); pick(e.dataTransfer.files?.[0] || null); }}
        >
          <input
            ref={inputRef}
            type="file"
            accept="application/pdf"
            style={{ display: "none" }}
            onChange={(e) => pick(e.target.files?.[0] || null)}
          />
          {file ? (
            <span style={s.fileName}>📄 {file.name}</span>
          ) : (
            <span style={s.dropHint}>Drag a PDF here, or click to choose</span>
          )}
        </div>

        <button
          style={{ ...s.btn, opacity: !file || status === "working" ? 0.6 : 1 }}
          onClick={convert}
          disabled={!file || status === "working"}
        >
          {status === "working" ? "Converting…" : "Convert to Australian format"}
        </button>

        {status === "done" && (
          <p style={s.ok}>✅ Done — your draft has downloaded. Open it in Word to make final edits.</p>
        )}
        {error && <p style={s.err}>⚠️ {error}</p>}

        <p style={s.note}>
          This produces a professional draft, not a final resume. Review and edit
          before sending. We never fabricate experience — only what’s in your file.
        </p>
      </div>
    </main>
  );
}

const s: Record<string, React.CSSProperties> = {
  main: { minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center",
          background: "#faf6f0", fontFamily: "system-ui, sans-serif", padding: 20 },
  card: { background: "#fff", border: "1px solid #ece3d6", borderRadius: 20, padding: 32,
          maxWidth: 520, width: "100%", boxShadow: "0 4px 14px rgba(28,25,23,.06)" },
  h1: { fontSize: 24, margin: "0 0 8px", color: "#1c1917" },
  sub: { fontSize: 14, color: "#756c5f", lineHeight: 1.5, margin: "0 0 20px" },
  drop: { border: "2px dashed", borderRadius: 16, padding: 32, textAlign: "center",
          cursor: "pointer", background: "#fff5ed", marginBottom: 16 },
  dropHint: { color: "#756c5f", fontSize: 14 },
  fileName: { color: "#1c1917", fontWeight: 600, fontSize: 14 },
  btn: { width: "100%", padding: "12px 20px", border: "none", borderRadius: 999,
         background: "linear-gradient(135deg,#bc4514,#e8742c)", color: "#fff",
         fontWeight: 600, fontSize: 15, cursor: "pointer" },
  ok: { color: "#2f6b34", fontSize: 14, marginTop: 14 },
  err: { color: "#b3261e", fontSize: 14, marginTop: 14 },
  note: { fontSize: 12, color: "#756c5f", marginTop: 18, lineHeight: 1.5 },
};
