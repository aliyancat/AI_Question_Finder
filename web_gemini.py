#!/usr/bin/env python3
"""
PaperCode Web — Web-based version of run_gemini.py
Maps past paper questions to your syllabus using Google Gemini AI.
"""

import os
import sys
import re
import time
from pathlib import Path
from datetime import datetime

import fitz  # PyMuPDF
from google import genai
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.resolve()

# Load .env file at startup
load_dotenv(BASE_DIR / ".env")
OUTPUT_DIR_PDFS    = BASE_DIR / "output_pdfs"
OUTPUT_DIR_HTML    = BASE_DIR / "output_html"
OUTPUT_DIR_REPORTS = BASE_DIR / "output_reports"

OUTPUT_DIR_PDFS.mkdir(exist_ok=True)
OUTPUT_DIR_HTML.mkdir(exist_ok=True)
OUTPUT_DIR_REPORTS.mkdir(exist_ok=True)

# ── Globals ──────────────────────────────────────────────────────────────────
ALL_FOLDERS = sorted(
    [d for d in BASE_DIR.iterdir() if d.is_dir() and not d.name.startswith(("output", "templates", "__pycache__", ".git", "PP_Downloader", ".venv", ".vscode", "."))],
    key=lambda d: d.name.lower()
)

app = Flask(__name__)
app.secret_key = "papercode-secret-key-change-in-production"


@app.template_filter("datetimeformat")
def datetimeformat_filter(value):
    """Format a timestamp (from os.stat) into a readable date string."""
    from datetime import datetime as dt
    return dt.fromtimestamp(value).strftime("%Y-%m-%d %H:%M:%S")


# ── Helpers (from run_gemini.py) ─────────────────────────────────────────────

def is_marking_scheme(pdf_path):
    name = pdf_path.stem.lower()
    return name.endswith(" ms") or name.endswith("-ms") or name.endswith("_ms") or name.endswith("ms")


def sanitize_filename(text, max_length=100):
    match = re.match(r'([^.!?]*[.!?])', text.strip())
    if match:
        first_sentence = match.group(1).strip()
    else:
        first_sentence = text.strip()[:max_length]
    filename = re.sub(r'[<>:"/\\|?*]', '', first_sentence)
    filename = re.sub(r'\s+', '_', filename)
    filename = filename[:max_length]
    return filename


def get_unique_filename(output_dir, base_name):
    stem = Path(base_name).stem
    suffix = Path(base_name).suffix
    candidate = output_dir / base_name
    if not candidate.exists():
        return candidate
    counter = 2
    while True:
        new_name = f"{stem}({counter}){suffix}"
        candidate = output_dir / new_name
        if not candidate.exists():
            return candidate
        counter += 1


def find_marking_scheme(question_pdf, all_pdfs):
    candidates = [
        f"{question_pdf.stem} ms",
        f"{question_pdf.stem}-ms",
        f"{question_pdf.stem}_ms",
        f"{question_pdf.stem}ms"
    ]
    for pdf in all_pdfs:
        if pdf.stem.lower() in [c.lower() for c in candidates]:
            return pdf
    return None


def find_page_in_ms(ms_path, q_num):
    try:
        doc = fitz.open(ms_path)
        clean_q = q_num.lower().replace("q", "").strip()
        match = re.search(r'\d+', clean_q)
        base_q = match.group(0) if match else clean_q
        best_page = 1
        found_base = False
        for page_num, page in enumerate(doc, 1):
            text = page.get_text().lower()
            if clean_q and clean_q in text:
                doc.close()
                return page_num
            if not found_base and base_q:
                pattern = rf"(?m)^(question\s*{base_q}|{base_q}[\s\(])"
                if re.search(pattern, text):
                    best_page = page_num
                    found_base = True
        doc.close()
        return best_page
    except Exception:
        return 1


def generate_html_report(result, question_pdfs, all_pdfs, output_dir, base_name):
    """Generate an interactive HTML report with clickable PDF links."""
    css = """
        :root {
            --bg-cream: #FFFEF5; --ink: #111111; --text-gray: #4B5563;
            --brand-indigo: #6366F1; --brand-pink: #EC4899;
            --pastel-yellow: #FDE68A; --butter-yellow: #FFF3B0;
            --pastel-lavender: #D8B4FE; --pastel-blue: #BAE6FD;
            --pastel-mint: #86EFAC; --pastel-peach: #FDBA74;
            --pastel-coral: #FF6B4A; --pastel-pink: #FBCFE8;
            --radius-card: 16px; --radius-pill: 999px;
            --shadow-hard: 4px 4px 0px var(--ink);
            --shadow-hard-hover: 2px 2px 0px var(--ink);
            --shadow-lift: 6px 6px 0px var(--ink);
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Poppins', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
               background: var(--bg-cream); color: var(--ink); min-height: 100vh; padding: 0;
               position: relative; overflow-x: hidden; }
        .blob { position: fixed; border-radius: 50%; z-index: 0; pointer-events: none; }
        .blob-1 { width: 340px; height: 340px; background: var(--butter-yellow); top: -100px; left: -120px; opacity: 0.6; }
        .blob-2 { width: 280px; height: 280px; background: var(--pastel-lavender); bottom: -80px; right: -100px; opacity: 0.5; }
        .blob-3 { width: 200px; height: 200px; background: var(--pastel-blue); top: 45%; right: 3%; opacity: 0.35; }
        .tilt-square { position: fixed; z-index: 0; pointer-events: none; }
        .tilt-1 { width: 90px; height: 90px; background: var(--pastel-pink); border: 2px solid var(--ink); top: 12%; right: 6%; transform: rotate(15deg); opacity: 0.7; }
        .tilt-2 { width: 70px; height: 70px; background: var(--pastel-mint); border: 2px solid var(--ink); bottom: 15%; left: 4%; transform: rotate(-12deg); opacity: 0.7; }
        .navbar { max-width: 900px; margin: 0 auto; padding: 24px 20px; display: flex; align-items: center; justify-content: space-between; position: relative; z-index: 2; }
        .logo { display: flex; align-items: center; gap: 12px; }
        .logo-icon { width: 44px; height: 44px; background: var(--brand-indigo); border: 2px solid var(--ink); border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 22px; box-shadow: 2px 2px 0px var(--ink); }
        .logo-word { font-weight: 800; font-size: 1.2em; color: var(--ink); line-height: 1; }
        .logo-tag { font-size: 0.72em; color: var(--brand-indigo); font-style: italic; font-weight: 500; }
        .hero { max-width: 900px; margin: 0 auto; padding: 10px 20px 30px; text-align: center; position: relative; z-index: 2; }
        .hero-badge { display: inline-flex; align-items: center; gap: 8px; background: var(--pastel-yellow); border: 2px solid var(--ink); border-radius: var(--radius-pill); padding: 6px 16px; font-size: 0.8em; font-weight: 700; margin-bottom: 20px; box-shadow: 2px 2px 0px var(--ink); }
        .hero-badge .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--brand-pink); }
        .hero h1 { font-size: 2.6em; color: var(--ink); font-weight: 900; letter-spacing: -1.5px; line-height: 1.1; margin-bottom: 14px; }
        .hero h1 .accent { color: var(--brand-indigo); }
        .hero h1 .highlight-box { background: var(--pastel-yellow); border: 2px solid var(--ink); border-radius: 10px; padding: 2px 14px; display: inline-block; transform: rotate(-2deg); box-shadow: 2px 2px 0px var(--ink); }
        .hero h1 .highlight-box .pink-text { color: var(--brand-pink); font-weight: 900; }
        .hero p { color: var(--text-gray); font-size: 1.05em; font-weight: 500; max-width: 560px; margin: 0 auto; line-height: 1.6; }
        .content { max-width: 900px; margin: 0 auto; padding: 0 20px 40px; position: relative; z-index: 2; }
        .section { margin-bottom: 32px; }
        .source-title { background: var(--pastel-blue); border: 2px solid var(--ink); border-radius: var(--radius-pill);
                        padding: 8px 20px; margin-bottom: 16px; font-weight: 700; color: var(--ink);
                        display: inline-block; box-shadow: 2px 2px 0px var(--ink); }
        .question-item { background: #FFFFFF; border: 2px solid var(--ink); border-radius: var(--radius-card);
                         padding: 24px; margin-bottom: 18px; box-shadow: var(--shadow-hard);
                         transition: transform 0.15s ease, box-shadow 0.15s ease; }
        .question-item:hover { transform: translate(-2px, -2px); box-shadow: var(--shadow-lift); }
        .question-text { color: var(--ink); font-size: 1em; line-height: 1.7; word-break: break-word; font-weight: 600; }
        .question-meta { font-size: 0.9em; color: var(--brand-indigo); margin-top: 10px; font-weight: 600;
                         display: inline-block; background: var(--pastel-blue); border: 2px solid var(--ink);
                         border-radius: var(--radius-pill); padding: 3px 12px; box-shadow: 1px 1px 0px var(--ink); }
        .button-row { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 18px; }
        .button { display: inline-flex; align-items: center; justify-content: center; gap: 6px;
                  padding: 12px 20px; border: 2px solid var(--ink); border-radius: var(--radius-pill);
                  font-weight: 700; font-size: 0.88em; text-decoration: none;
                  transition: transform 0.12s ease, box-shadow 0.12s ease; box-shadow: var(--shadow-hard); }
        .button:hover { transform: translate(2px, 2px); box-shadow: var(--shadow-hard-hover); }
        .button-primary { background: var(--brand-indigo); color: white; }
        .button-secondary { background: var(--pastel-mint); color: var(--ink); }
        .disabled { opacity: 0.4; cursor: not-allowed; pointer-events: none; }
        .no-match { text-align: center; padding: 60px 30px; color: var(--text-gray); font-size: 1.2em; font-weight: 600; }
        .footer { max-width: 900px; margin: 0 auto 40px; padding: 22px 30px; background: var(--pastel-blue);
                  border: 2px solid var(--ink); border-radius: var(--radius-card); box-shadow: var(--shadow-hard);
                  text-align: center; color: var(--ink); font-weight: 700; font-size: 0.9em;
                  position: relative; z-index: 2; }
        .footer .heart { color: var(--brand-pink); }
        @media (max-width: 600px) { .hero h1 { font-size: 1.8em; } .button-row { flex-direction: column; } .button { width: 100%; } }
    """

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Past Paper Questions</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>{css}</style>
</head>
<body>
    <div class="blob blob-1"></div>
    <div class="blob blob-2"></div>
    <div class="blob blob-3"></div>
    <div class="tilt-square tilt-1"></div>
    <div class="tilt-square tilt-2"></div>
    <nav class="navbar">
        <div class="logo">
            <div class="logo-icon">&#128209;</div>
            <div>
                <div class="logo-word">PaperCode</div>
                <div class="logo-tag">find your questions</div>
            </div>
        </div>
    </nav>
    <section class="hero">
        <div class="hero-badge">
            <span class="dot"></span>
            AI-Powered Syllabus Matching
        </div>
        <h1>
            Past Paper <span class="accent">Questions</span><br>
            <span class="highlight-box"><span class="pink-text">Matched</span></span> to Your Syllabus
        </h1>
        <p>Click a question to open the PDF, then check the marking scheme.</p>
    </section>
    <div class="content">
"""

    if "No questions match" in result:
        html_content += '<div class="no-match">No questions match the syllabus.</div>'
    else:
        current_section = None
        for line in result.splitlines():
            line = line.strip()
            if line.startswith("From "):
                if current_section:
                    html_content += '</div>'
                current_section = line
                html_content += f'<div class="section"><div class="source-title">{line}</div>'
            elif line.startswith("- Q"):
                parts = line[2:].split(":", 1)
                if len(parts) >= 2:
                    q_num = parts[0].strip()
                    q_text = parts[1].strip()
                    if current_section:
                        match = re.search(r'From\s+([^\|]+)\s*\|\s*Page\s+(\d+)', current_section)
                        if match:
                            pdf_name = match.group(1).strip()
                            page_num = match.group(2)
                            pdf_path = next((p for p in question_pdfs if p.stem.lower() == pdf_name.lower()), None)
                            if pdf_path:
                                # Use Flask route to serve PDFs instead of file:/// URIs
                                pdf_rel = pdf_path.relative_to(BASE_DIR).as_posix()
                                paper_link = f"/view/{pdf_rel}#page={page_num}"
                                ms_path = find_marking_scheme(pdf_path, all_pdfs)
                                if ms_path:
                                    ms_page = find_page_in_ms(ms_path, q_num)
                                    ms_rel = ms_path.relative_to(BASE_DIR).as_posix()
                                    ms_link = f"/view/{ms_rel}#page={ms_page}"
                                else:
                                    ms_link = None
                                html_content += f'''
            <div class="question-item">
                <div class="question-text">{q_num}: {q_text}</div>
                <div class="question-meta">📍 {pdf_path.name} — Page {page_num}</div>
                <div class="button-row">
                    <a class="button button-primary" href="{paper_link}" target="_blank">Open question paper</a>
'''
                                if ms_link:
                                    html_content += f'                    <a class="button button-secondary" href="{ms_link}" target="_blank">Open marking scheme</a>\n'
                                else:
                                    html_content += '                    <span class="button button-secondary disabled">No marking scheme found</span>\n'
                                html_content += "                </div>\n            </div>\n"
                            else:
                                html_content += f'''
            <div class="question-item" style="opacity:0.6;">
                <div class="question-text">{q_num}: {q_text}</div>
                <div class="question-meta">⚠️ PDF not found: {pdf_name}</div>
            </div>
'''
        if current_section:
            html_content += '</div>'

    html_content += """
        </div>
        <div class="footer">
            Generated by PaperCode | Open questions and marking schemes locally
        </div>
    </div>
</body>
</html>
"""
    html_path = get_unique_filename(output_dir, f"{base_name}.html")
    html_path.write_text(html_content, encoding="utf-8")
    return html_path


def load_api_key():
    """Load GEMINI_API_KEY from env, .env file, or provided value."""
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        env_file = BASE_DIR / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("GEMINI_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"\'')
                    break
    return key


def process_papers(folder_name, syllabus_text, api_key):
    """Core processing: extract PDF text, call Gemini, save reports.
    Returns (success, result_dict)."""
    papers_dir = BASE_DIR / folder_name

    # Gather PDFs
    all_pdfs = sorted(papers_dir.glob("*.pdf")) if papers_dir.exists() else []
    if not all_pdfs:
        return False, {"error": f"No PDFs found in '{folder_name}/'."}

    question_pdfs = [p for p in all_pdfs if not is_marking_scheme(p)]
    scheme_pdfs = [p for p in all_pdfs if is_marking_scheme(p)]
    if not question_pdfs:
        return False, {"error": f"No question paper PDFs found in '{folder_name}/'."}

    # Read PDFs
    papers_text = ""
    for pdf in question_pdfs:
        doc = fitz.open(str(pdf))
        papers_text += f"\n\n=== {pdf.stem} ===\n"
        for page_num, page in enumerate(doc, 1):
            papers_text += f"\n[PAGE {page_num}]\n{page.get_text()}"
        doc.close()

    # Build prompt
    prompt_text = f"""You are a strict examiner mapping past paper questions to a specific syllabus.
Here is the syllabus:
{syllabus_text}

Here are the past paper questions (with page numbers marked as [PAGE N]):
{papers_text}

Analyze EACH past paper question and determine if it is EXPLICITLY covered by the syllabus.
Beware of superficial keyword matches (e.g., 'magnetic' in computer storage vs. 'magnetism' in physics).
If the question is about a different subject or context than the syllabus, it is NOT covered.

Output requirements:
If NO questions strictly match the syllabus, output EXACTLY: "No questions match the syllabus."
If there are matches, list the matching questions in the following format:

From [lowercase pdf name] | Page [page number]:
- Q[number]: [Exact question text]

IMPORTANT: Include the page number where each question appears.
Only include the question text, not answers.
Keep the output concise."""

    # Call Gemini
    client = genai.Client(api_key=api_key)
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt_text,
        )
        result = response.text
    except Exception as e:
        return False, {"error": f"Gemini API call failed: {e}"}

    # Save outputs
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = sanitize_filename(syllabus_text)

    # Text report
    report_path = get_unique_filename(OUTPUT_DIR_REPORTS, f"{base_name}_report.txt")
    report_path.write_text(result, encoding="utf-8")

    # PDF report
    pdf_report_path = None
    if "No questions match" not in result:
        pdf_report_path = get_unique_filename(OUTPUT_DIR_PDFS, f"{base_name}.pdf")
        doc = SimpleDocTemplate(str(pdf_report_path), pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        for line in result.splitlines():
            line = line.strip()
            if line.startswith("From "):
                story.append(Paragraph(line, styles['Heading2']))
                story.append(Spacer(1, 12))
            elif line.startswith("- Q"):
                story.append(Paragraph(line[2:], styles['Normal']))
                story.append(Spacer(1, 12))
        doc.build(story)

    # HTML report
    html_path = generate_html_report(result, question_pdfs, all_pdfs, OUTPUT_DIR_HTML, base_name)

    return True, {
        "result": result,
        "report_path": str(report_path.relative_to(BASE_DIR)).replace("\\", "/"),
        "html_path": str(html_path.relative_to(BASE_DIR)).replace("\\", "/"),
        "pdf_path": str(pdf_report_path.relative_to(BASE_DIR)).replace("\\", "/") if pdf_report_path else None,
        "question_count": len(question_pdfs),
        "scheme_count": len(scheme_pdfs),
        "folder_name": folder_name,
        "base_name": base_name,
    }


# ── Flask Routes ─────────────────────────────────────────────────────────────

@app.route("/")
def index():
    folders = []
    for d in ALL_FOLDERS:
        pdf_count = len(list(d.glob("*.pdf")))
        folders.append({"name": d.name, "path": str(d), "pdf_count": pdf_count})
    return render_template("index.html", folders=folders)


@app.route("/run", methods=["POST"])
def run():
    folder_name = request.form.get("folder", "").strip()
    syllabus_text = request.form.get("syllabus", "").strip()
    api_key = request.form.get("api_key", "").strip() or load_api_key()

    if not folder_name:
        flash("Please select a past papers folder.", "danger")
        return redirect(url_for("index"))
    if not syllabus_text:
        flash("Please paste your syllabus.", "danger")
        return redirect(url_for("index"))
    if not api_key:
        flash("GEMINI_API_KEY not found. Provide it in the form or set it as an environment variable.", "danger")
        return redirect(url_for("index"))

    success, data = process_papers(folder_name, syllabus_text, api_key)

    if not success:
        flash(data.get("error", "Unknown error"), "danger")
        return redirect(url_for("index"))

    return render_template("results.html", data=data)


@app.route("/output/<path:filepath>")
def serve_output(filepath):
    """Serve generated output files (HTML, text, PDF) via HTTP."""
    from flask import send_file
    # filepath is relative to BASE_DIR (e.g. "output_html/file.html")
    target = BASE_DIR / filepath
    if target.exists() and target.is_file():
        return send_file(str(target))
    flash(f"File not found: {filepath}", "danger")
    return redirect(url_for("index"))


@app.route("/view/<path:filepath>")
def serve_file(filepath):
    """Serve any file from the project directory (PDFs, etc.) via HTTP.
    Used by the generated HTML reports for "Open question paper" and "Open marking scheme" buttons.
    """
    from flask import send_file
    # filepath is relative to BASE_DIR (e.g. "past_papers_ella_compsci_p2/June-2022.pdf")
    target = BASE_DIR / filepath
    if target.exists() and target.is_file():
        return send_file(str(target))
    flash(f"File not found: {filepath}", "danger")
    return redirect(url_for("index"))


@app.route("/history")
def history():
    """Show past reports."""
    def get_file_info(files, subdir):
        result = []
        for f in sorted(files, key=lambda p: p.stat().st_mtime, reverse=True):
            result.append({
                "name": f.name,
                "rel_path": f"{subdir}/{f.name}",
                "mtime": f.stat().st_mtime,
            })
        return result
        return result

    html_files = get_file_info(list(OUTPUT_DIR_HTML.glob("*.html")), "output_html")
    reports    = get_file_info(list(OUTPUT_DIR_REPORTS.glob("*.txt")), "output_reports")
    pdf_files  = get_file_info(list(OUTPUT_DIR_PDFS.glob("*.pdf")), "output_pdfs")
    return render_template("history.html", reports=reports[:50], html_files=html_files[:50], pdf_files=pdf_files[:50])


if __name__ == "__main__":
    import webbrowser
    print("  ╔══════════════════════════════════════════╗")
    print("  ║     PaperCode Web — Gemini Edition       ║")
    print("  ╚══════════════════════════════════════════╝")
    print(f"\n  Open your browser and go to: http://127.0.0.1:5000\n")
    webbrowser.open("http://127.0.0.1:5000")
    app.run(debug=True, host="127.0.0.1", port=5000)
