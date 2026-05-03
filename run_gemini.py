import os
import sys
import time
from pathlib import Path
from datetime import datetime

try:
    import fitz
except ImportError:
    sys.exit("Missing dependency: pip install PyMuPDF")

try:
    from google import genai
except ImportError:
    sys.exit("Missing dependency: pip install google-genai")

try:
    from colorama import init, Fore, Back, Style
    init(autoreset=True)
    HAS_COLOR = True
except ImportError:
    HAS_COLOR = False
    class Fore:
        RED=CYAN=BLUE=MAGENTA=GREEN=YELLOW=WHITE=BLACK=""
    class Back:
        RED=CYAN=BLUE=MAGENTA=GREEN=YELLOW=WHITE=BLACK=RESET=""
    class Style:
        BRIGHT=DIM=RESET_ALL=""

try:
    import pyfiglet
    HAS_FIG = True
except ImportError:
    HAS_FIG = False

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
except ImportError:
    sys.exit("Missing dependency: pip install reportlab")

PAPERS_DIR = Path("past_papers")
OUTPUT_DIR_PDFS = Path("output_pdfs")
OUTPUT_DIR_HTML = Path("output_html")
OUTPUT_DIR_REPORTS = Path("output_reports")

# Create output directories
OUTPUT_DIR_PDFS.mkdir(exist_ok=True)
OUTPUT_DIR_HTML.mkdir(exist_ok=True)
OUTPUT_DIR_REPORTS.mkdir(exist_ok=True)

CORAL  = "\033[38;2;210;100;80m"
CORAL2 = "\033[38;2;240;140;110m"
DARK   = "\033[38;2;80;40;30m"
RESET  = "\033[0m"

def clear():
    os.system("cls" if os.name == "nt" else "clear")

def print_banner():
    if HAS_FIG:
        code  = pyfiglet.figlet_format("ALIYAN CODE",  font="larry3d")
    else:
        code  = "  ALIYAN CODE\n"

    def render_3d(text):
        lines = text.splitlines()
        for line in lines:
            print(DARK + "   " + line + RESET)
        rows = len(lines)
        print(f"\033[{rows}A", end="")
        for line in lines:
            print(CORAL + line + RESET)

    print()
    render_3d(code)
    print()

def print_info_box():
    msg = "  *  PaperCode — map past paper questions to your syllabus (Gemini)  "
    border = "─" * len(msg)
    if HAS_COLOR:
        print(Fore.YELLOW + "  ┌" + border + "┐" + Style.RESET_ALL)
        print(Fore.YELLOW + "  │" + Style.RESET_ALL + Style.BRIGHT + msg + Style.RESET_ALL + Fore.YELLOW + "│" + Style.RESET_ALL)
        print(Fore.YELLOW + "  └" + border + "┘" + Style.RESET_ALL)
    else:
        print("  +" + border + "+")
        print("  |" + msg + "|")
        print("  +" + border + "+")
    print()

def print_tips():
    if HAS_COLOR:
        print(f"  {Style.BRIGHT}Tips for getting started:{Style.RESET_ALL}")
        print(f"  {Fore.WHITE}1. Select your past papers folder from the list when prompted.{Style.RESET_ALL}")
        print(f"  {Fore.WHITE}2. Paste your syllabus when prompted — be as detailed as possible.{Style.RESET_ALL}")
        print(f"  {Fore.WHITE}3. Your report will be saved to  output/  when done.{Style.RESET_ALL}")
    else:
        print("  Tips for getting started:")
        print("  1. Select your past papers folder from the list when prompted.")
        print("  2. Paste your syllabus when prompted — be as detailed as possible.")
        print("  3. Your report will be saved to  output/  when done.")
    print()

def divider():
    line = "  " + "─" * 62
    print((Fore.WHITE + Style.DIM + line + Style.RESET_ALL) if HAS_COLOR else line)

def step(msg):
    sym = (CORAL + "◆ " + RESET) if HAS_COLOR else "* "
    print(f"  {sym}{msg}")

def ok(msg):
    col = (Fore.GREEN + Style.BRIGHT) if HAS_COLOR else ""
    rst = Style.RESET_ALL if HAS_COLOR else ""
    print(f"  {col}✔ {msg}{rst}")

def generate_html_report(result, question_pdfs, all_pdfs, output_dir, timestamp, syllabus):
    """Generate an interactive HTML report with clickable PDF links."""
    
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Past Paper Questions</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 40px 20px;
        }
        
        .container {
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            font-weight: 700;
        }
        
        .header p {
            font-size: 1.1em;
            opacity: 0.9;
        }
        
        .content {
            padding: 40px 30px;
        }
        
        .section {
            margin-bottom: 40px;
        }
        
        .source-title {
            background: #f8f9ff;
            border-left: 4px solid #667eea;
            padding: 15px 20px;
            margin-bottom: 15px;
            border-radius: 4px;
            font-weight: 600;
            color: #333;
        }
        
        .question-item {
            background: #ffffff;
            border: 1px solid #e0e0e0;
            border-radius: 12px;
            padding: 22px 24px;
            margin-bottom: 18px;
            transition: all 0.25s ease;
        }
        
        .question-item:hover {
            border-color: #667eea;
            box-shadow: 0 8px 26px rgba(102, 126, 234, 0.12);
            transform: translateY(-2px);
        }
        
        .question-text {
            color: #212121;
            font-size: 1em;
            line-height: 1.7;
            word-break: break-word;
        }
        
        .question-meta {
            font-size: 0.95em;
            color: #667eea;
            margin-top: 10px;
            font-weight: 600;
        }
        
        .button-row {
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            margin-top: 18px;
        }
        
        .button {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: 12px 18px;
            border-radius: 999px;
            font-weight: 700;
            text-decoration: none;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        
        .button-primary {
            background: #667eea;
            color: white;
        }
        
        .button-secondary {
            background: #f5f7ff;
            color: #333;
            border: 1px solid #dbe3ff;
        }
        
        .button:hover {
            transform: translateY(-1px);
            box-shadow: 0 8px 22px rgba(102, 126, 234, 0.15);
        }
        
        .disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        .no-match {
            text-align: center;
            padding: 60px 30px;
            color: #999;
            font-size: 1.2em;
        }
        
        .footer {
            background: #f8f9ff;
            padding: 20px 30px;
            text-align: center;
            color: #666;
            font-size: 0.95em;
            border-top: 1px solid #e0e0e0;
        }
        
        @media (max-width: 600px) {
            .header h1 {
                font-size: 1.8em;
            }
            
            .content {
                padding: 20px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📄 Past Paper Questions</h1>
            <p>Click a question to open the PDF; use the second button for marking schemes.</p>
        </div>
        
        <div class="content">
"""
    
    def find_marking_scheme(question_pdf):
        candidates = [
            f"{question_pdf.stem} ms",
            f"{question_pdf.stem}-ms",
            f"{question_pdf.stem}_ms",
            f"{question_pdf.stem}ms"
        ]
        for pdf in all_pdfs:
            if pdf.stem.lower() in [candidate.lower() for candidate in candidates]:
                return pdf
        return None

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
                        import re
                        match = re.search(r'From\s+([^\|]+)\s*\|\s*Page\s+(\d+)', current_section)
                        if match:
                            pdf_name = match.group(1).strip()
                            page_num = match.group(2)
                            
                            pdf_path = None
                            for pdf in question_pdfs:
                                if pdf.stem.lower() == pdf_name.lower():
                                    pdf_path = pdf
                                    break
                            
                            if pdf_path:
                                paper_link = pdf_path.resolve().as_uri() + f"#page={page_num}"
                                ms_path = find_marking_scheme(pdf_path)
                                ms_link = ms_path.resolve().as_uri() + f"#page={page_num}" if ms_path else None
                                
                                html_content += f'''
                <div class="question-item">
                    <div class="question-text">{q_num}: {q_text}</div>
                    <div class="question-meta">📍 {pdf_path.name} — Page {page_num}</div>
                    <div class="button-row">
                        <a class="button button-primary" href="{paper_link}" target="_blank">Open question paper</a>
                        '''
                                if ms_link:
                                    html_content += f'<a class="button button-secondary" href="{ms_link}" target="_blank">Open marking scheme</a>'
                                else:
                                    html_content += '<span class="button button-secondary disabled">No marking scheme found</span>'
                                html_content += "\n                    </div>\n                </div>\n"
                            else:
                                html_content += f'''
                <div class="question-item" style="opacity: 0.6;">
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
    
    # Save HTML file with syllabus-based name
    filename = sanitize_filename(syllabus) + ".html"
    html_path = output_dir / filename
    html_path.write_text(html_content, encoding="utf-8")
    return html_path

def err(msg):
    col = (Fore.RED + Style.BRIGHT) if HAS_COLOR else ""
    rst = Style.RESET_ALL if HAS_COLOR else ""
    print(f"  {col}✘ {msg}{rst}")
    sys.exit(1)

def sanitize_filename(text, max_length=100):
    """Extract first sentence and sanitize it for use as a filename."""
    import re
    # Get first sentence (up to period, question mark, or exclamation)
    match = re.match(r'([^.!?]*[.!?])', text.strip())
    if match:
        first_sentence = match.group(1).strip()
    else:
        first_sentence = text.strip()[:max_length]
    
    # Remove invalid filename characters
    filename = re.sub(r'[<>:"/\\|?*]', '', first_sentence)
    filename = re.sub(r'\s+', '_', filename)  # Replace spaces with underscores
    filename = filename[:max_length]
    return filename

def footer(pdf_count):
    col = (Fore.WHITE + Style.DIM) if HAS_COLOR else ""
    hi  = (Fore.CYAN + Style.BRIGHT) if HAS_COLOR else ""
    rst = Style.RESET_ALL if HAS_COLOR else ""
    print()
    divider()
    print(f"  {col}papers/{rst}  {hi}{pdf_count} PDF(s){rst}   {col}model/{rst}  {hi}gemini-2.5-flash{rst}")
    divider()

def main():
    clear()
    print_banner()
    print_info_box()
    print_tips()
    divider()
    print()

    # API key
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key and Path(".env").exists():
        for line in Path(".env").read_text().splitlines():
            if line.startswith("GEMINI_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"\'')
    if not key:
        err("GEMINI_API_KEY not found. Add it to a .env file or set it as an env variable.")

    ok("API key loaded")

    # Select past papers folder
    divider()
    if HAS_COLOR:
        print(f"\n  {Style.BRIGHT}Select your past papers folder from the list below:{Style.RESET_ALL}\n")
    else:
        print("\n  Select your past papers folder from the list below:\n")

    current_dir = Path.cwd()
    dirs = [d for d in current_dir.iterdir() if d.is_dir()]
    if not dirs:
        err("No folders found in the current directory.")

    for i, d in enumerate(dirs, 1):
        print(f"  {i}. {d.name}")

    print()
    while True:
        try:
            choice = int(input("Enter the number of the folder: ").strip())
            if 1 <= choice <= len(dirs):
                selected_dir = dirs[choice - 1]
                break
            else:
                print("Invalid number. Please try again.")
        except ValueError:
            print("Please enter a valid number.")

    papers_dir = selected_dir
    print()
    ok(f"Selected folder: {papers_dir.name}")

    all_pdfs = sorted(papers_dir.glob("*.pdf")) if papers_dir.exists() else []
    if not all_pdfs:
        err(f"No PDFs found in '{papers_dir}/'. Add your past papers there and retry.")

    question_pdfs = [pdf for pdf in all_pdfs if not is_marking_scheme(pdf)]
    scheme_pdfs = [pdf for pdf in all_pdfs if is_marking_scheme(pdf)]
    if not question_pdfs:
        err(f"No question paper PDFs found in '{papers_dir}/'. Make sure your question papers are not marked as marking schemes.")

    ok(f"Found {len(question_pdfs)} question paper(s) in {papers_dir}/")
    if scheme_pdfs:
        step(f"Detected {len(scheme_pdfs)} marking scheme(s) in {papers_dir}/")
    print()

    # Syllabus
    divider()
    if HAS_COLOR:
        print(f"\n  {Style.BRIGHT}Paste your syllabus below.{Style.RESET_ALL}  {Fore.WHITE}{Style.DIM}Press Enter on a blank line when done.{Style.RESET_ALL}\n")
    else:
        print("\n  Paste your syllabus below. Press Enter on a blank line when done.\n")

    lines = []
    while True:
        try:
            ln = input("    ")
        except EOFError:
            break
        if not ln.strip():
            break
        lines.append(ln)

    if not lines:
        err("No syllabus provided. Exiting.")

    syllabus = "\n".join(lines)
    print()
    ok(f"Syllabus captured ({len(lines)} lines)")

    # Read PDFs
    print()
    divider()
    print()
    step(f"Reading {len(pdfs)} PDF(s)...\n")
    papers_text = ""
    for pdf in pdfs:
        col = (Fore.CYAN + Style.DIM) if HAS_COLOR else ""
        rst = Style.RESET_ALL if HAS_COLOR else ""
        print(f"    {col}↳ {pdf.name}{rst}")
        doc  = fitz.open(str(pdf))
        papers_text += f"\n\n=== {pdf.stem} ===\n"
        for page_num, page in enumerate(doc, 1):
            text = page.get_text()
            papers_text += f"\n[PAGE {page_num}]\n{text}"
        doc.close()

    print()
    ok(f"Text extracted from {len(pdfs)} file(s)")

    prompt_text = f"""You are a strict examiner mapping past paper questions to a specific syllabus.
Here is the syllabus:
{syllabus}

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
    print()
    divider()
    print()
    step("Sending to Gemini (gemini-2.5-flash)...")
    print()

    client = genai.Client(api_key=key)
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt_text,
        )
        result = response.text
    except Exception as e:
        err(f"Failed to generate content: {e}")

    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = OUTPUT_DIR_REPORTS / f"report_{ts}.txt"
    out.write_text(result, encoding="utf-8")
    ok(f"Report saved → {out}")

    # Generate PDF if there are questions
    if "No questions match" not in result:
        pdf_out = OUTPUT_DIR_PDFS / f"questions_{ts}.pdf"
        doc = SimpleDocTemplate(str(pdf_out), pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        current_source = ""
        for line in result.splitlines():
            line = line.strip()
            if line.startswith("From "):
                current_source = line
                story.append(Paragraph(current_source, styles['Heading2']))
                story.append(Spacer(1, 12))
            elif line.startswith("- Q"):
                question = line[2:]  # Remove the "- "
                story.append(Paragraph(question, styles['Normal']))
                story.append(Spacer(1, 12))
        doc.build(story)
        ok(f"Questions PDF saved → {pdf_out}")
    
    # Generate interactive HTML report
    print()
    html_path = generate_html_report(result, question_pdfs, all_pdfs, OUTPUT_DIR_HTML, ts, syllabus)
    ok(f"Interactive HTML saved → {html_path}")
    if HAS_COLOR:
        print(f"  {Fore.CYAN}→ Open this file in your browser to view clickable links{Style.RESET_ALL}")
    print()

    print()
    divider()
    if HAS_COLOR:
        print(f"\n  {Style.BRIGHT}RESULTS{Style.RESET_ALL}\n")
    else:
        print("\n  RESULTS\n")

    for line in result.splitlines():
        if line.strip():
            col = Fore.GREEN if HAS_COLOR else ""
            rst = Style.RESET_ALL if HAS_COLOR else ""
            print(f"  {col}{line}{rst}")
        else:
            print()

    footer(len(pdfs))
    print()

if __name__ == "__main__":
    main()
