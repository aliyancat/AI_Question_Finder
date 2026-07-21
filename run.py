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

# ── Pastel palette (truecolor) — matches design-style-prompt.md ──
INDIGO   = "\033[38;2;99;102;241m"   # brand indigo #6366F1
PINK     = "\033[38;2;236;72;153m"   # brand pink #EC4899
LAVENDER = "\033[38;2;168;85;247m"   # vivid lavender (readable)
SKY      = "\033[38;2;14;165;233m"   # vivid sky blue
SUNFLOWER= "\033[38;2;234;179;8m"     # warm yellow #FDE68A-ish
PEACH    = "\033[38;2;251;146;60m"    # peach #FDBA74
CORAL    = "\033[38;2;255;107;74m"    # coral #FF6B4A
MINT     = "\033[38;2;22;163;74m"     # mint green (readable)
INK      = "\033[38;2;17;17;17m"      # ink black #111111
GRAY     = "\033[38;2;75;85;99m"      # charcoal gray #4B5563
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
        print(INDIGO + "  " + line + RESET)
    print()

def print_info_box():
    msg = "  map past paper questions to your syllabus  "
    border = "=" * len(msg)
    if HAS_COLOR:
        print(INK + "  +" + border + "+" + RESET)
        print(INK + "  |" + RESET + Style.BRIGHT + PINK + msg + RESET + INK + "|" + RESET)
        print(INK + "  +" + border + "+" + RESET)
    else:
        print("  +" + border + "+")
        print("  |" + msg + "|")
        print("  +" + border + "+")
    print()

def print_tips():
    if HAS_COLOR:
        print(f"  {Style.BRIGHT}{INDIGO}Tips for getting started:{RESET}")
        print(f"  {PINK}1.{RESET} Select your past papers folder from the list when prompted.")
        print(f"  {PINK}2.{RESET} Paste your syllabus when prompted - be as detailed as possible.")
        print(f"  {PINK}3.{RESET} Your report will be saved to  output/  when done.")
    else:
        print("  Tips for getting started:")
        print("  1. Select your past papers folder from the list when prompted.")
        print("  2. Paste your syllabus when prompted - be as detailed as possible.")
        print("  3. Your report will be saved to  output/  when done.")
    print()

def divider():
    line = "  " + "-" * 62
    print((Style.DIM + INK + line + RESET) if HAS_COLOR else line)

def step(msg):
    sym = (CORAL + "> " + RESET) if HAS_COLOR else "* "
    print(f"  {sym}{msg}")

def ok(msg):
    col = (MINT + Style.BRIGHT) if HAS_COLOR else ""
    rst = Style.RESET_ALL if HAS_COLOR else ""
    print(f"  {col}[OK] {msg}{rst}")

def generate_html_report(result, pdfs, output_dir, timestamp, syllabus):
    """Generate an interactive HTML report with clickable PDF links."""

    # Pastel card backgrounds to rotate through (design system palette)
    pastel_cards = ["#FFFFFF", "#FDE68A", "#FFFFFF", "#D8B4FE", "#FFFFFF", "#BAE6FD", "#FFFFFF", "#86EFAC"]
    # Icon chip colors (rounded square on left of each card)
    chip_colors  = ["#FDE68A", "#D8B4FE", "#BAE6FD", "#86EFAC", "#FDBA74", "#FBCFE8", "#FF6B4A", "#E0E7FF"]
    # Status pill: background + text color pairs
    status_colors = [
        ("#DCFCE7", "#16A34A"),  # success/matched
        ("#E0E7FF", "#4F46E5"),  # info
        ("#D1FAE5", "#059669"),  # verified
        ("#FFEDD5", "#EA580C"),  # warning
    ]
    status_labels = ["Matched", "Info", "Verified", "Matched"]
    # Trust badge strip colors
    trust_badges = [
        ("#FDE68A", "&#128221;", "Syllabus Mapped"),
        ("#D8B4FE", "&#129504;", "AI Powered"),
        ("#BAE6FD", "&#128202;", "Past Papers"),
        ("#86EFAC", "&#9989;", "Verified"),
        ("#FDBA74", "&#128218;", "Click to Open"),
    ]

    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Past Paper Questions</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-cream: #FFFEF5;
            --ink: #111111;
            --text-gray: #4B5563;
            --brand-indigo: #6366F1;
            --brand-pink: #EC4899;
            --pastel-yellow: #FDE68A;
            --butter-yellow: #FFF3B0;
            --pastel-lavender: #D8B4FE;
            --pastel-blue: #BAE6FD;
            --pastel-mint: #86EFAC;
            --pastel-peach: #FDBA74;
            --pastel-coral: #FF6B4A;
            --pastel-pink: #FBCFE8;
            --border-w: 2px;
            --radius-card: 16px;
            --radius-pill: 999px;
            --shadow-hard: 4px 4px 0px var(--ink);
            --shadow-hard-hover: 2px 2px 0px var(--ink);
            --shadow-lift: 6px 6px 0px var(--ink);
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Poppins', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
               background: var(--bg-cream); color: var(--ink); min-height: 100vh; padding: 0;
               position: relative; overflow-x: hidden; }

        /* ── Decorative background shapes (Memphis-inspired) ── */
        .blob { position: fixed; border-radius: 50%; z-index: 0; pointer-events: none; }
        .blob-1 { width: 340px; height: 340px; background: var(--butter-yellow); top: -100px; left: -120px; opacity: 0.6; }
        .blob-2 { width: 280px; height: 280px; background: var(--pastel-lavender); bottom: -80px; right: -100px; opacity: 0.5; }
        .blob-3 { width: 200px; height: 200px; background: var(--pastel-blue); top: 45%; right: 3%; opacity: 0.35; }
        .tilt-square { position: fixed; z-index: 0; pointer-events: none; }
        .tilt-1 { width: 90px; height: 90px; background: var(--pastel-pink); border: 2px solid var(--ink);
                  top: 12%; right: 6%; transform: rotate(15deg); opacity: 0.7; }
        .tilt-2 { width: 70px; height: 70px; background: var(--pastel-mint); border: 2px solid var(--ink);
                  bottom: 15%; left: 4%; transform: rotate(-12deg); opacity: 0.7; }

        /* ── Navbar ── */
        .navbar { max-width: 900px; margin: 0 auto; padding: 24px 20px; display: flex;
                  align-items: center; justify-content: space-between; position: relative; z-index: 2; }
        .logo { display: flex; align-items: center; gap: 12px; }
        .logo-icon { width: 44px; height: 44px; background: var(--brand-indigo); border: 2px solid var(--ink);
                      border-radius: 12px; display: flex; align-items: center; justify-content: center;
                      font-size: 22px; box-shadow: 2px 2px 0px var(--ink); }
        .logo-text { display: flex; flex-direction: column; }
        .logo-word { font-weight: 800; font-size: 1.2em; color: var(--ink); line-height: 1; }
        .logo-tag { font-size: 0.72em; color: var(--brand-indigo); font-style: italic; font-weight: 500; }
        .nav-cta { background: #16A34A; color: #FFF; border: 2px solid var(--ink); border-radius: var(--radius-pill);
                   padding: 8px 20px; font-weight: 700; font-size: 0.85em; box-shadow: var(--shadow-hard);
                   transition: transform 0.12s ease, box-shadow 0.12s ease; cursor: pointer; text-decoration: none;
                   display: inline-flex; align-items: center; gap: 6px; }
        .nav-cta:hover { transform: translate(2px, 2px); box-shadow: var(--shadow-hard-hover); }

        /* ── Hero section ── */
        .hero { max-width: 900px; margin: 0 auto; padding: 20px 20px 40px; text-align: center; position: relative; z-index: 2; }
        .hero-badge { display: inline-flex; align-items: center; gap: 8px; background: var(--pastel-yellow);
                      border: 2px solid var(--ink); border-radius: var(--radius-pill); padding: 6px 16px;
                      font-size: 0.8em; font-weight: 700; margin-bottom: 24px; box-shadow: 2px 2px 0px var(--ink); }
        .hero-badge .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--brand-pink); }
        .hero h1 { font-size: 3em; color: var(--ink); font-weight: 900; letter-spacing: -1.5px; line-height: 1.1;
                   margin-bottom: 16px; }
        .hero h1 .accent { color: var(--brand-indigo); }
        .hero h1 .highlight-box { background: var(--pastel-yellow); border: 2px solid var(--ink);
                                   border-radius: 10px; padding: 2px 14px; display: inline-block;
                                   transform: rotate(-2deg); box-shadow: 2px 2px 0px var(--ink); }
        .hero h1 .highlight-box .pink-text { color: var(--brand-pink); font-weight: 900; }
        .hero p { color: var(--text-gray); font-size: 1.1em; font-weight: 500; max-width: 560px;
                  margin: 0 auto; line-height: 1.6; }

        /* ── Trust badge strip ── */
        .trust-strip { max-width: 900px; margin: 0 auto 32px; padding: 16px 20px; position: relative; z-index: 2;
                       display: flex; flex-wrap: wrap; gap: 10px; justify-content: center;
                       border-top: 2px solid var(--ink); border-bottom: 2px solid var(--ink); }
        .trust-pill { display: inline-flex; align-items: center; gap: 6px; border: 2px solid var(--ink);
                      border-radius: var(--radius-pill); padding: 5px 14px; font-size: 0.78em; font-weight: 700;
                      box-shadow: 1px 1px 0px var(--ink); }

        /* ── Content cards ── */
        .content { max-width: 900px; margin: 0 auto; padding: 0 20px 40px; position: relative; z-index: 2; }
        .card { border: 2px solid var(--ink); border-radius: var(--radius-card); padding: 20px 24px;
                margin-bottom: 16px; box-shadow: var(--shadow-hard);
                transition: transform 0.15s ease, box-shadow 0.15s ease; }
        .card:hover { transform: translate(-2px, -2px) scale(1.02); box-shadow: var(--shadow-lift); }
        .card a { text-decoration: none; color: inherit; display: flex; align-items: flex-start; gap: 16px; }
        .icon-chip { width: 48px; height: 48px; min-width: 48px; border: 2px solid var(--ink); border-radius: 12px;
                     display: flex; align-items: center; justify-content: center; font-size: 24px;
                     box-shadow: 2px 2px 0px var(--ink); }
        .card-body { flex: 1; }
        .card-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
        .card-title { color: var(--ink); font-size: 1.02em; line-height: 1.5; font-weight: 700; }
        .status-pill { font-size: 0.72em; font-weight: 700; padding: 4px 12px; border-radius: var(--radius-pill);
                       border: 2px solid var(--ink); white-space: nowrap; box-shadow: 1px 1px 0px var(--ink); }
        .card-meta { font-size: 0.8em; color: var(--text-gray); margin-top: 10px; font-weight: 500;
                     display: flex; align-items: center; gap: 6px; }
        .card-meta .sep { color: var(--ink); opacity: 0.3; }

        .no-match { text-align: center; padding: 70px 30px; color: var(--text-gray); font-size: 1.15em; font-weight: 600; }

        /* ── Footer ── */
        .footer { max-width: 900px; margin: 0 auto 40px; padding: 22px 30px; background: var(--pastel-blue);
                  border: 2px solid var(--ink); border-radius: var(--radius-card); box-shadow: var(--shadow-hard);
                  text-align: center; color: var(--ink); font-weight: 700; font-size: 0.9em;
                  position: relative; z-index: 2; }
        .footer .heart { color: var(--brand-pink); }

        @media (max-width: 600px) {
            .hero h1 { font-size: 2em; }
            .card a { flex-direction: column; gap: 12px; }
            .icon-chip { width: 40px; height: 40px; min-width: 40px; font-size: 20px; }
        }
    </style>
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
            <div class="logo-text">
                <span class="logo-word">PaperCode</span>
                <span class="logo-tag">find your questions</span>
            </div>
        </div>
        <a class="nav-cta" href="javascript:window.scrollTo({top:document.body.scrollHeight,behavior:'smooth'})">
            View Results &#8595;
        </a>
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
        <p>Every question below has been mapped to your syllabus by AI. Click any card to open the original PDF.</p>
    </section>

    <div class="trust-strip">
"""

    # Build trust badge pills
    for bg, icon, label in trust_badges:
        html_content += f'        <span class="trust-pill" style="background:{bg};">{icon} {label}</span>\n'
    html_content += '    </div>\n\n    <div class="content">\n'

    if "No questions match" in result:
        html_content += '<div class="no-match">No questions match the syllabus.</div>'
    else:
        card_idx = 0
        for line in result.splitlines():
            line = line.strip()
            if not line:
                continue

            parts = line.split(" - ")
            if len(parts) >= 2:
                pdf_name = parts[0].strip()
                question_text = " - ".join(parts[1:])

                pdf_path = None
                for pdf in pdfs:
                    if pdf.stem.lower() in pdf_name.lower():
                        pdf_path = pdf
                        break

                card_bg = pastel_cards[card_idx % len(pastel_cards)]
                chip_bg = chip_colors[card_idx % len(chip_colors)]
                status_bg, status_text_col = status_colors[card_idx % len(status_colors)]
                status_label = status_labels[card_idx % len(status_labels)]
                card_idx += 1

                if pdf_path:
                    file_link = f"file:///{pdf_path.absolute()}#page=1"
                    html_content += f'''        <div class="card" style="background:{card_bg};">
            <a href="{file_link}" title="Open {pdf_path.name}">
                <div class="icon-chip" style="background:{chip_bg};">&#128196;</div>
                <div class="card-body">
                    <div class="card-top">
                        <div class="card-title">{question_text}</div>
                        <span class="status-pill" style="background:{status_bg};color:{status_text_col};">{status_label}</span>
                    </div>
                    <div class="card-meta">
                        <span>&#128205; {pdf_path.name}</span>
                        <span class="sep">&bull;</span>
                        <span>&#128279; Click to open PDF</span>
                    </div>
                </div>
            </a>
        </div>
'''
                else:
                    html_content += f'''        <div class="card" style="background:{card_bg};">
            <div class="icon-chip" style="background:{chip_bg};">&#128196;</div>
            <div class="card-body">
                <div class="card-top">
                    <div class="card-title">{line}</div>
                    <span class="status-pill" style="background:{status_bg};color:{status_text_col};">{status_label}</span>
                </div>
            </div>
        </div>
'''

    html_content += """    </div>
    <div class="footer">
        Generated by PaperCode <span class="heart">&#10084;</span> Click any card to open the PDF
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
    print(f"  {col}[ERROR] {msg}{rst}")
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
    dim = (Style.DIM + GRAY) if HAS_COLOR else ""
    hi  = (INDIGO + Style.BRIGHT) if HAS_COLOR else ""
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
        print(f"\n  {Style.BRIGHT}{INDIGO}Select your past papers folder from the list below:{RESET}\n")
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
        print(f"\n  {Style.BRIGHT}{INDIGO}Paste your syllabus below.{RESET}  {Style.DIM}{GRAY}Press Enter on a blank line when done.{RESET}\n")
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
        col = (LAVENDER + Style.DIM) if HAS_COLOR else ""
        rst = RESET if HAS_COLOR else ""
        print(f"    {col}> {pdf.name}{rst}")
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
    ok(f"Report saved > {out}")

    # Generate interactive HTML report
    print()
    html_path = generate_html_report(result, pdfs, OUTPUT_DIR_HTML, ts, syllabus)
    ok(f"Interactive HTML saved > {html_path}")
    if HAS_COLOR:
        print(f"  {INDIGO}> Open this file in your browser to view clickable links{RESET}")

    print()
    divider()
    if HAS_COLOR:
        print(f"\n  {Style.BRIGHT}{PINK}RESULTS{RESET}\n")
    else:
        print("\n  RESULTS\n")

    for line in result.splitlines():
        if line.strip():
            col = INDIGO if HAS_COLOR else ""
            rst = RESET if HAS_COLOR else ""
            print(f"  {col}{line}{rst}")
        else:
            print()

    footer(len(pdfs))
    print()

if __name__ == "__main__":
    main()