import os
import sys
import time
from pathlib import Path
from datetime import datetime

# Ensure UTF-8 output so pastel/box-drawing characters render correctly
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    import fitz
except ImportError:
    sys.exit("Missing dependency: pip install PyMuPDF")

try:
    from groq import Groq
except ImportError:
    sys.exit("Missing dependency: pip install groq")

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

PAPERS_DIR = Path("past_papers")
OUTPUT_DIR_PDFS = Path("output_pdfs")
OUTPUT_DIR_HTML = Path("output_html")
OUTPUT_DIR_REPORTS = Path("output_reports")

# Create output directories
OUTPUT_DIR_PDFS.mkdir(exist_ok=True)
OUTPUT_DIR_HTML.mkdir(exist_ok=True)
OUTPUT_DIR_REPORTS.mkdir(exist_ok=True)

# ── Pastel palette (truecolor) ──────────────────────────────
LAVENDER = "\033[38;2;168;85;247m"   # vivid lavender (readable)
SKY      = "\033[38;2;14;165;233m"   # vivid sky blue
SUNFLOWER= "\033[38;2;234;179;8m"     # warm yellow
PEACH    = "\033[38;2;251;146;60m"    # peach
CORAL    = "\033[38;2;239;68;68m"     # coral red
MINT     = "\033[38;2;16;185;129m"   # mint green
GRAPE    = "\033[38;2;124;58;237m"    # grape purple
INK      = "\033[38;2;63;63;70m"      # soft ink (dark)
RESET    = "\033[0m"

def clear():
    os.system("cls" if os.name == "nt" else "clear")

def print_banner():
    if HAS_FIG:
        code  = pyfiglet.figlet_format("PaperCode", font="small")
    else:
        code  = "  PaperCode\n"

    print()
    for line in code.splitlines():
        print(LAVENDER + "  " + line + RESET)
    print()

def print_info_box():
    msg = "  map past paper questions to your syllabus  "
    border = "━" * len(msg)
    if HAS_COLOR:
        print(SKY + "  ┏" + border + "┓" + RESET)
        print(SKY + "  ┃" + RESET + Style.BRIGHT + SUNFLOWER + msg + RESET + SKY + "┃" + RESET)
        print(SKY + "  ┗" + border + "┛" + RESET)
    else:
        print("  +" + border + "+")
        print("  |" + msg + "|")
        print("  +" + border + "+")
    print()

def print_tips():
    if HAS_COLOR:
        print(f"  {Style.BRIGHT}{GRAPE}Tips for getting started:{RESET}")
        print(f"  {MINT}1.{RESET} Select your past papers folder from the list when prompted.")
        print(f"  {MINT}2.{RESET} Paste your syllabus when prompted — be as detailed as possible.")
        print(f"  {MINT}3.{RESET} Your report will be saved to  output/  when done.")
    else:
        print("  Tips for getting started:")
        print("  1. Select your past papers folder from the list when prompted.")
        print("  2. Paste your syllabus when prompted — be as detailed as possible.")
        print("  3. Your report will be saved to  output/  when done.")
    print()

def divider():
    line = "  " + "•" * 62
    print((Style.DIM + line + Style.RESET_ALL) if HAS_COLOR else line)

def step(msg):
    sym = (PEACH + "▸ " + RESET) if HAS_COLOR else "* "
    print(f"  {sym}{msg}")

def ok(msg):
    col = (MINT + Style.BRIGHT) if HAS_COLOR else ""
    rst = Style.RESET_ALL if HAS_COLOR else ""
    print(f"  {col}✔ {msg}{rst}")

def generate_html_report(result, pdfs, output_dir, timestamp, syllabus):
    """Generate an interactive HTML report with clickable PDF links."""
    
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Past Paper Questions</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Quicksand', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
               background: #FFF8F0;
               background-image: radial-gradient(circle at 10% 20%, #D8B4FE22 0%, transparent 40%),
                                 radial-gradient(circle at 90% 80%, #BAE6FD22 0%, transparent 40%),
                                 radial-gradient(circle at 50% 50%, #FDE68A11 0%, transparent 50%);
               min-height: 100vh; padding: 40px 20px; }
        .container { max-width: 900px; margin: 0 auto; background: #FFFFFF;
                     border: 4px solid #1F2937; border-radius: 28px;
                     box-shadow: 8px 8px 0 #1F2937; overflow: hidden; }
        .header { background: #FDE68A; border-bottom: 4px solid #1F2937;
                  padding: 44px 30px; text-align: center; position: relative; }
        .header h1 { font-size: 2.4em; color: #1F2937; font-weight: 800; letter-spacing: -0.5px; }
        .header p { color: #6B7280; margin-top: 8px; font-weight: 600; }
        .badge { display: inline-block; background: #FF6B4A; color: #FFF; padding: 4px 14px;
                 border-radius: 999px; font-size: 0.75em; font-weight: 700; margin-bottom: 14px;
                 border: 2px solid #1F2937; }
        .content { padding: 36px 30px; }
        .question-item { background: #FDF2F8; border: 3px solid #1F2937; border-radius: 18px;
                        padding: 18px 22px; margin-bottom: 16px; transition: transform 0.15s ease, box-shadow 0.15s ease;
                        box-shadow: 4px 4px 0 #1F2937; }
        .question-item:hover { transform: translate(-2px, -2px); box-shadow: 6px 6px 0 #1F2937; }
        .question-item a { text-decoration: none; color: inherit; display: block; }
        .question-text { color: #1F2937; font-size: 1.02em; line-height: 1.6; font-weight: 600; }
        .question-meta { font-size: 0.85em; color: #7C3AED; margin-top: 10px; font-weight: 700;
                         display: inline-block; background: #EDE9FE; padding: 3px 10px;
                         border-radius: 999px; border: 2px solid #1F2937; }
        .no-match { text-align: center; padding: 60px 30px; color: #6B7280; font-size: 1.1em; font-weight: 600; }
        .footer { background: #BAE6FD; border-top: 4px solid #1F2937; padding: 20px 30px;
                  text-align: center; color: #1F2937; font-weight: 700; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <span class="badge">📄 PAPER QUESTIONS</span>
            <h1>Past Paper Questions</h1>
            <p>Click any question to open the PDF</p>
        </div>
        <div class="content">
"""
    
    if "No questions match" in result:
        html_content += '<div class="no-match">No questions match the syllabus.</div>'
    else:
        for line in result.splitlines():
            line = line.strip()
            if not line:
                continue
            
            # Parse line and create clickable link
            parts = line.split(" - ")
            if len(parts) >= 2:
                pdf_name = parts[0].strip()
                question_text = " - ".join(parts[1:])
                
                # Find matching PDF
                pdf_path = None
                for pdf in pdfs:
                    if pdf.stem.lower() in pdf_name.lower():
                        pdf_path = pdf
                        break
                
                if pdf_path:
                    file_link = f"file:///{pdf_path.absolute()}#page=1"
                    html_content += f'''<div class="question-item">
                        <a href="{file_link}" title="Open {pdf_path.name}">
                            <div class="question-text">{question_text}</div>
                            <div class="question-meta">📍 {pdf_path.name}</div>
                        </a>
                    </div>
'''
                else:
                    html_content += f'<div class="question-item"><div class="question-text">{line}</div></div>\n'
    
    html_content += """        </div>
        <div class="footer">
            Generated by PaperCode | Click questions to open PDFs
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
    col = (CORAL + Style.BRIGHT) if HAS_COLOR else ""
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
    dim = (Style.DIM + INK) if HAS_COLOR else ""
    hi  = (GRAPE + Style.BRIGHT) if HAS_COLOR else ""
    rst = Style.RESET_ALL if HAS_COLOR else ""
    print()
    divider()
    print(f"  {dim}papers/{rst}  {hi}{pdf_count} PDF(s){rst}   {dim}model/{rst}  {hi}llama-3.3-70b{rst}")
    divider()

def main():
    clear()
    print_banner()
    print_info_box()
    print_tips()
    divider()
    print()

    # API key
    key = os.environ.get("GROQ_API_KEY", "")
    if not key and Path(".env").exists():
        for line in Path(".env").read_text().splitlines():
            if line.startswith("GROQ_API_KEY=") or line.startswith("GROQ_API="):
                key = line.split("=", 1)[1].strip().strip('"\'')
    if not key:
        err("GROQ_API_KEY not found. Add it to a .env file or set it as an env variable.")

    ok("API key loaded")

    # Select past papers folder
    divider()
    if HAS_COLOR:
        print(f"\n  {Style.BRIGHT}{GRAPE}Select your past papers folder from the list below:{RESET}\n")
    else:
        print("\n  Select your past papers folder from the list below:\n")

    current_dir = Path.cwd()
    dirs = [d for d in current_dir.iterdir() if d.is_dir()]
    if not dirs:
        err("No folders found in the current directory.")

    for i, d in enumerate(dirs, 1):
        num = (SUNFLOWER + Style.BRIGHT) if HAS_COLOR else ""
        rst = RESET if HAS_COLOR else ""
        print(f"  {num}{i}.{rst} {d.name}")

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

    pdfs = sorted(papers_dir.glob("*.pdf")) if papers_dir.exists() else []
    if not pdfs:
        err(f"No PDFs found in '{papers_dir}/'. Add your past papers there and retry.")

    ok(f"Found {len(pdfs)} past paper(s) in {papers_dir}/")
    print()

    # Syllabus
    divider()
    if HAS_COLOR:
        print(f"\n  {Style.BRIGHT}{GRAPE}Paste your syllabus below.{RESET}  {Style.DIM}{INK}Press Enter on a blank line when done.{RESET}\n")
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
        col = (SKY + Style.DIM) if HAS_COLOR else ""
        rst = RESET if HAS_COLOR else ""
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

Here are the past paper questions:
{papers_text}

Analyze EACH past paper question and determine if it is EXPLICITLY covered by the syllabus.
Beware of superficial keyword matches (e.g., 'magnetic' in computer storage vs. 'magnetism' in physics).
If the question is about a different subject or context than the syllabus, it is NOT covered.

Output requirements:
If NO questions strictly match the syllabus, output EXACTLY: "No questions match the syllabus."
If there are matches, format them strictly as:
[lowercase pdf name] - Q[numbers] - [Exact syllabus point number and text]

CRITICAL RULES:
1. ONLY include questions that are 100% relevant to the syllabus context.
2. DO NOT output the question text or answers. Output the exact syllabus point it matches.
3. Keep the output extremely concise."""

    # Call Groq
    print()
    divider()
    print()
    step("Sending to Groq  (llama-3.3-70b-versatile)...")
    print()

    client = Groq(api_key=key)
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt_text}]
    )
    result = completion.choices[0].message.content

    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = OUTPUT_DIR_REPORTS / f"report_{ts}.txt"
    out.write_text(result, encoding="utf-8")
    ok(f"Report saved → {out}")

    # Generate interactive HTML report
    print()
    html_path = generate_html_report(result, pdfs, OUTPUT_DIR_HTML, ts, syllabus)
    ok(f"Interactive HTML saved → {html_path}")
    if HAS_COLOR:
        print(f"  {SKY}→ Open this file in your browser to view clickable links{RESET}")

    print()
    divider()
    if HAS_COLOR:
        print(f"\n  {Style.BRIGHT}{LAVENDER}RESULTS{RESET}\n")
    else:
        print("\n  RESULTS\n")

    for line in result.splitlines():
        if line.strip():
            col = MINT if HAS_COLOR else ""
            rst = RESET if HAS_COLOR else ""
            print(f"  {col}{line}{rst}")
        else:
            print()

    footer(len(pdfs))
    print()

if __name__ == "__main__":
    main()