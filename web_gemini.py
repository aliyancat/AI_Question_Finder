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

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.resolve()
OUTPUT_DIR_PDFS    = BASE_DIR / "output_pdfs"
OUTPUT_DIR_HTML    = BASE_DIR / "output_html"
OUTPUT_DIR_REPORTS = BASE_DIR / "output_reports"

OUTPUT_DIR_PDFS.mkdir(exist_ok=True)
OUTPUT_DIR_HTML.mkdir(exist_ok=True)
OUTPUT_DIR_REPORTS.mkdir(exist_ok=True)

# ── Globals ──────────────────────────────────────────────────────────────────
ALL_FOLDERS = sorted(
    [d for d in BASE_DIR.iterdir() if d.is_dir() and not d.name.startswith(("output", "templates", "__pycache__", ".git", "PP_Downloader"))],
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
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
               background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
               min-height: 100vh; padding: 40px 20px; }
        .container { max-width: 900px; margin: 0 auto; background: white; border-radius: 12px;
                     box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3); overflow: hidden; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;
                  padding: 40px 30px; text-align: center; }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; font-weight: 700; }
        .header p { font-size: 1.1em; opacity: 0.9; }
        .content { padding: 40px 30px; }
        .section { margin-bottom: 40px; }
        .source-title { background: #f8f9ff; border-left: 4px solid #667eea; padding: 15px 20px;
                        margin-bottom: 15px; border-radius: 4px; font-weight: 600; color: #333; }
        .question-item { background: #ffffff; border: 1px solid #e0e0e0; border-radius: 12px;
                         padding: 22px 24px; margin-bottom: 18px; transition: all 0.25s ease; }
        .question-item:hover { border-color: #667eea; box-shadow: 0 8px 26px rgba(102,126,234,0.12);
                               transform: translateY(-2px); }
        .question-text { color: #212121; font-size: 1em; line-height: 1.7; word-break: break-word; }
        .question-meta { font-size: 0.95em; color: #667eea; margin-top: 10px; font-weight: 600; }
        .button-row { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 18px; }
        .button { display: inline-flex; align-items: center; justify-content: center;
                  padding: 12px 18px; border-radius: 999px; font-weight: 700; text-decoration: none;
                  transition: transform 0.2s ease, box-shadow 0.2s ease; }
        .button-primary { background: #667eea; color: white; }
        .button-secondary { background: #f5f7ff; color: #333; border: 1px solid #dbe3ff; }
        .button:hover { transform: translateY(-1px); box-shadow: 0 8px 22px rgba(102,126,234,0.15); }
        .disabled { opacity: 0.5; cursor: not-allowed; }
        .no-match { text-align: center; padding: 60px 30px; color: #999; font-size: 1.2em; }
        .footer { background: #f8f9ff; padding: 20px 30px; text-align: center; color: #666;
                  font-size: 0.95em; border-top: 1px solid #e0e0e0; }
        @media (max-width: 600px) { .header h1 { font-size: 1.8em; } .content { padding: 20px; } }
    """

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Past Paper Questions</title>
    <style>{css}</style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📄 Past Paper Questions</h1>
            <p>Click a question to open the PDF; use the second button for marking schemes.</p>
        </div>
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
                                paper_link = pdf_path.resolve().as_uri() + f"#page={page_num}"
                                ms_path = find_marking_scheme(pdf_path, all_pdfs)
                                if ms_path:
                                    ms_page = find_page_in_ms(ms_path, q_num)
                                    ms_link = ms_path.resolve().as_uri() + f"#page={ms_page}"
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
        "report_path": str(report_path.relative_to(BASE_DIR)),
        "html_path": str(html_path.relative_to(BASE_DIR)),
        "pdf_path": str(pdf_report_path.relative_to(BASE_DIR)) if pdf_report_path else None,
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
    api_key = request.form.get("api_key", "").strip() or os.environ.get("GEMINI_API_KEY", "")

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

    return render_template("results.html", data=data, BASE_DIR=BASE_DIR)


@app.route("/history")
def history():
    """Show past reports."""
    reports = sorted(OUTPUT_DIR_REPORTS.glob("*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)
    html_files = sorted(OUTPUT_DIR_HTML.glob("*.html"), key=lambda p: p.stat().st_mtime, reverse=True)
    pdf_files = sorted(OUTPUT_DIR_PDFS.glob("*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True)
    return render_template("history.html", reports=reports[:50], html_files=html_files[:50], pdf_files=pdf_files[:50])


if __name__ == "__main__":
    import webbrowser
    print("  ╔══════════════════════════════════════════╗")
    print("  ║     PaperCode Web — Gemini Edition       ║")
    print("  ╚══════════════════════════════════════════╝")
    print(f"\n  Open your browser and go to: http://127.0.0.1:5000\n")
    webbrowser.open("http://127.0.0.1:5000")
    app.run(debug=True, host="127.0.0.1", port=5000)
