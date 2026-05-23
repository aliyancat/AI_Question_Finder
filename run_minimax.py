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
    from openai import OpenAI
except ImportError:
    sys.exit("Missing dependency: pip install openai")

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

def is_marking_scheme(pdf_path):
    name = pdf_path.stem.lower()
    return name.endswith(" ms") or name.endswith("-ms") or name.endswith("_ms") or name.endswith("ms")


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
    msg = "  *  PaperCode — map past paper questions to your syllabus (MiniMax)  "
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

def extract_pdf_info(line, question_pdfs):\n    \"\"\"Extract PDF name and page number from various output formats.\"\"\"\n    import re\n    \n    # Clean the line - remove markdown bold/italic markers\n    clean_line = re.sub(r'\\*+', '', line)\n    \n    # Try format 1: \"From pdfname | Page X:\"\n    match = re.search(r'From\\s+([A-Za-z0-9_\\-]+)\\s*\\|\\s*Page\\s+(\\d+)', clean_line, re.IGNORECASE)\n    if match:\n        return match.group(1).lower(), match.group(2)\n    \n    # Try format 2: \"pdfname | Page X\" (no \"From\")\n    match = re.search(r'^([A-Za-z0-9_\\-]+)\\s*\\|\\s*Page\\s+(\\d+)', clean_line, re.IGNORECASE)\n    if match:\n        return match.group(1).lower(), match.group(2)\n    \n    # Try format 3: Extract \"From Jun-2019\" style\n    match = re.search(r'[Ff]rom\\s+([A-Za-z0-9_\\-]+)', clean_line)\n    if match:\n        pdf_name = match.group(1).lower()\n        # Try to find page number nearby\n        page_match = re.search(r'[Pp]age\\s*(\\d+)', clean_line)\n        page = page_match.group(1) if page_match else \"1\"\n        return pdf_name, page\n    \n    # Try format 4: Match question number and try to find PDF from list\n    # e.g. \"Q6(a)(ii)\" or \"Q10(a)\"\n    q_match = re.search(r'Q(\\d+)', line)\n    if q_match:\n        q_num = q_match.group(1)\n        # Try each PDF to see which one has this question\n        for pdf in question_pdfs:\n            pdf_path = Path(pdf)\n            try:\n                doc = fitz.open(str(pdf_path))\n                text = \"\"\n                for page in doc:\n                    text += page.get_text().lower()\n                doc.close()\n                if f\"question {q_num}\" in text or f\"q{q_num}\" in text:\n                    return pdf.stem.lower(), \"1\"\n            except:\n                pass\n    \n    return None, None\n\n\ndef find_marking_scheme(question_pdf):\n    candidates = [\n        f\"{question_pdf.stem} ms\",\n        f\"{question_pdf.stem}-ms\",\n        f\"{question_pdf.stem}_ms\",\n        f\"{question_pdf.stem}ms\"\n    ]\n    for pdf in all_pdfs:\n        if pdf.stem.lower() in [candidate.lower() for candidate in candidates]:\n            return pdf\n    return None\n\n\ndef find_page_in_ms(ms_path, q_num):\n    try:\n        import re\n        import fitz\n        doc = fitz.open(ms_path)\n        \n        clean_q = q_num.lower().replace(\"q\", \"\").strip()\n        match = re.search(r'\\d+', clean_q)\n        base_q = match.group(0) if match else clean_q\n        \n        best_page = 1\n        found_base = False\n        \n        for page_num, page in enumerate(doc, 1):\n            text = page.get_text().lower()\n            \n            if clean_q and clean_q in text:\n                doc.close()\n                return page_num\n            \n            if not found_base and base_q:\n                pattern = rf\"(?m)^(question\\s*{base_q}|{base_q}[\\s\\(])\"\n                if re.search(pattern, text):\n                    best_page = page_num\n                    found_base = True\n        \n        doc.close()\n        return best_page\n    except Exception:\n        return 1\n\n\ndef generate_html_report(result, question_pdfs, all_pdfs, output_dir, timestamp, syllabus):\n    \"\"\"Generate an interactive HTML report with clickable PDF links.\"\"\"\n    \n    html_content = \"\"\"<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n    <meta charset=\"UTF-8\">\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n    <title>Past Paper Questions</title>\n    <style>\n        * { margin: 0; padding: 0; box-sizing: border-box; }\n        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; \n               background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);\n               min-height: 100vh; padding: 40px 20px; }\n        .container { max-width: 900px; margin: 0 auto; background: white; border-radius: 12px;\n                     box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3); overflow: hidden; }\n        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;\n                  padding: 40px 30px; text-align: center; }\n        .header h1 { font-size: 2.5em; margin-bottom: 10px; }\n        .content { padding: 40px 30px; }\n        .question-item { background: #ffffff; border: 1px solid #e0e0e0; border-radius: 12px;\n                        padding: 20px 24px; margin-bottom: 16px; transition: all 0.3s ease; }\n        .question-item:hover { border-color: #667eea; box-shadow: 0 8px 25px rgba(102, 126, 234, 0.15); \n                              transform: translateY(-2px); }\n        .question-source { background: #f0f4ff; border-left: 4px solid #667eea; padding: 12px 16px;\n                          margin-bottom: 14px; border-radius: 6px; font-weight: 600; color: #333; }\n        .question-text { color: #333; font-size: 1em; line-height: 1.6; margin-bottom: 14px; }\n        .question-meta { font-size: 0.9em; color: #667eea; margin-bottom: 12px; font-weight: 600; }\n        .button-row { display: flex; flex-wrap: wrap; gap: 10px; }\n        .button { display: inline-flex; align-items: center; justify-content: center;\n                  padding: 10px 18px; border-radius: 999px; font-weight: 700; text-decoration: none;\n                  transition: transform 0.2s ease, box-shadow 0.2s ease; }\n        .button-primary { background: #667eea; color: white; }\n        .button-secondary { background: #f5f7ff; color: #333; border: 1px solid #dbe3ff; }\n        .button:hover { transform: translateY(-1px); box-shadow: 0 6px 20px rgba(102, 126, 234, 0.2); }\n        .no-match { text-align: center; padding: 60px 30px; color: #999; font-size: 1.2em; }\n        .footer { background: #f8f9ff; padding: 20px 30px; text-align: center; color: #666; font-size: 0.9em; }\n        .warning { background: #fff3cd; border: 1px solid #ffc107; padding: 15px; border-radius: 8px; margin-bottom: 15px; }\n        @media (max-width: 600px) { .header h1 { font-size: 1.8em; } .content { padding: 20px; } }\n    </style>\n</head>\n<body>\n    <div class=\"container\">\n        <div class=\"header\">\n            <h1>📄 Past Paper Questions</h1>\n            <p>Click to open PDFs with marking scheme links</p>\n        </div>\n        <div class=\"content\">\n\"\"\"\n    \n    if \"No questions match\" in result:\n        html_content += '<div class=\"no-match\">No questions match the syllabus.</div>'\n    else:\n        # Group questions by their source (every few lines that talk about same paper)\n        questions = []\n        for line in result.splitlines():\n            line = line.strip()\n            if not line:\n                continue\n            \n            # Check if line contains \"From\" or a question reference\n            if re.search(r'[Ff]rom\\s+|---\\s*Q\\d+', line) or re.search(r'Q\\d+[a-z]?\\(', line):\n                pdf_name, page_num = extract_pdf_info(line, question_pdfs)\n                \n                if pdf_name:\n                    # Find the actual PDF\n                    pdf_path = None\n                    for pdf in question_pdfs:\n                        if pdf.stem.lower() == pdf_name.lower():\n                            pdf_path = pdf\n                            break\n                    \n                    if pdf_path:\n                        # Extract question number from line\n                        q_match = re.search(r'Q(\\d+[a-z]?\\([a-z]?\\))', line, re.IGNORECASE)\n                        if not q_match:\n                            q_match = re.search(r'Q(\\d+)', line, re.IGNORECASE)\n                        q_num = q_match.group(1) if q_match else \"?\"\n                        \n                        # Try to find page in line\n                        page_match = re.search(r'[Pp]age\\s*(\\d+)', line)\n                        page = page_match.group(1) if page_match else \"1\"\n                        \n                        # Try to extract the actual question text\n                        # Look for quoted text or text after colon\n                        text_match = re.search(r'[\"\'](.+?)[\"\']', line)\n                        if text_match:\n                            q_text = text_match.group(1)\n                        else:\n                            # Use the whole line as description\n                            q_text = line[:200] + \"...\" if len(line) > 200 else line\n                        \n                        questions.append({\n                            'pdf_name': pdf_name,\n                            'pdf_path': pdf_path,\n                            'page': page,\n                            'q_num': q_num,\n                            'q_text': q_text,\n                            'line': line\n                        })\n        \n        # Deduplicate questions by (pdf_name, q_num)\n        seen = set()\n        for q in questions:\n            key = (q['pdf_name'], q['q_num'])\n            if key not in seen:\n                seen.add(key)\n                \n                # Create HTML for this question\n                paper_link = q['pdf_path'].resolve().as_uri() + f\"#page={q['page']}\"\n                ms_path = find_marking_scheme(q['pdf_path'])\n                \n                html_content += f'''<div class=\"question-item\">\n                    <div class=\"question-source\">From {q['pdf_name']}</div>\n                    <div class=\"question-text\">{q['line']}</div>\n                    <div class=\"question-meta\">📍 {q['pdf_path'].name} — Page {q['page']}</div>\n                    <div class=\"button-row\">\n                        <a class=\"button button-primary\" href=\"{paper_link}\" target=\"_blank\">Open question paper</a>\n                '''\n                \n                if ms_path:\n                    ms_page = find_page_in_ms(ms_path, q['q_num'])\n                    ms_link = ms_path.resolve().as_uri() + f\"#page={ms_page}\"\n                    html_content += f'<a class=\"button button-secondary\" href=\"{ms_link}\" target=\"_blank\">Open marking scheme</a>'\n                else:\n                    html_content += '<span class=\"button button-secondary\" style=\"opacity:0.5;\">No marking scheme</span>'\n                \n                html_content += \"\\n                    </div>\\n                </div>\\n\"\n    \n    html_content += \"\"\"\"        </div>\n        <div class=\"footer\">\n            Generated by PaperCode | Open questions and marking schemes locally\n        </div>\n    </div>\n</body>\n</html>\n\"\"\"\n    \n    filename = sanitize_filename(syllabus) + \".html\"\n    html_path = output_dir / filename\n    html_path.write_text(html_content, encoding=\"utf-8\")\n    return html_path"

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
    print(f"  {col}papers/{rst}  {hi}{pdf_count} PDF(s){rst}   {col}model/{rst}  {hi}MiniMax-M2.7{rst}")
    divider()

def main():
    clear()
    print_banner()
    print_info_box()
    print_tips()
    divider()
    print()

    # API key - MiniMax uses MINIMAX_API_KEY
    key = os.environ.get("MINIMAX_API_KEY", "")
    if not key and Path(".env").exists():
        for line in Path(".env").read_text().splitlines():
            if line.startswith("MINIMAX_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"\'')
    if not key:
        err("MINIMAX_API_KEY not found. Add it to a .env file or set it as an env variable.")

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
    step(f"Reading {len(question_pdfs)} PDF(s)...\n")
    papers_text = ""
    for pdf in question_pdfs:
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
    ok(f"Text extracted from {len(question_pdfs)} file(s)")

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

    # Call MiniMax
    print()
    divider()
    print()
    step("Sending to MiniMax (MiniMax-M2.7)...")
    print()

    client = OpenAI(
        api_key=key,
        base_url="https://api.minimax.io/v1"
    )
    
    try:
        response = client.chat.completions.create(
            model="MiniMax-M2.7",
            messages=[
                {
                    "role": "user", 
                    "content": prompt_text
                }
            ]
        )
        result = response.choices[0].message.content
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

    footer(len(question_pdfs))
    print()

if __name__ == "__main__":
    main()