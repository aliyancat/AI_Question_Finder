import os
import sys
import time
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from datetime import datetime

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    HAS_COLOR = True
except ImportError:
    HAS_COLOR = False
    class Fore:
        RED = CYAN = BLUE = MAGENTA = GREEN = YELLOW = WHITE = BLACK = ""
    class Style:
        BRIGHT = DIM = RESET_ALL = ""

try:
    import pyfiglet
    HAS_FIG = True
except ImportError:
    HAS_FIG = False

PAPERS_DIR = Path("past_papers")
PAPERS_DIR.mkdir(exist_ok=True)

BASE_URL = "https://papacambridge.com"

CORAL  = "\033[38;2;210;100;80m"
CORAL2 = "\033[38;2;240;140;110m"
DARK   = "\033[38;2;80;40;30m"
RESET  = "\033[0m"

def clear():
    os.system("cls" if os.name == "nt" else "clear")

def print_banner():
    if HAS_FIG:
        banner = pyfiglet.figlet_format("PAST PAPER\nDOWNLOADER", font="larry3d")
    else:
        banner = "  PAST PAPER DOWNLOADER\n"
    
    print()
    for line in banner.splitlines():
        print(DARK + "   " + line + RESET)
    print()
    for line in banner.splitlines():
        print(CORAL + line + RESET)
    print()

def divider():
    print("\n  " + "─" * 62 + "\n")

def step(msg):
    col = CORAL if HAS_COLOR else ""
    print(f"  {col}◆ {RESET}{msg}")

def ok(msg):
    col = (Fore.GREEN + Style.BRIGHT) if HAS_COLOR else ""
    rst = Style.RESET_ALL if HAS_COLOR else ""
    print(f"  {col}✔ {rst}{msg}")

def err(msg):
    col = (Fore.RED + Style.BRIGHT) if HAS_COLOR else ""
    rst = Style.RESET_ALL if HAS_COLOR else ""
    print(f"  {col}✘ {rst}{msg}")
    sys.exit(1)

def get_links(url, headers):
    """Fetch a page and extract all PDF links."""
    step(f"Fetching: {url}")
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        pdf_links = []
        
        # Find all links that point to PDFs
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.lower().endswith('.pdf') or 'pdf' in href.lower():
                full_url = urljoin(url, href)
                pdf_links.append((link.get_text(strip=True) or href, full_url))
        
        return pdf_links, soup
        
    except requests.RequestException as e:
        err(f"Failed to fetch {url}: {e}")

def get_category_links(url, headers):
    """Extract links to categories (subject folders)."""
    step(f"Fetching categories from: {url}")
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        category_links = []
        
        # Find all subject/category links
        for link in soup.find_all('a', href=True):
            href = link['href']
            text = link.get_text(strip=True)
            
            # Skip empty links and non-category links
            if not text or text.lower() in ['home', 'login', 'register', 'contact']:
                continue
            
            # Look for category links (usually contain /papers/ or are relative paths)
            if '/o-level/' in href or '/a-level/' in href or '/igcse/' in href:
                full_url = urljoin(BASE_URL, href)
                if full_url not in [c[1] for c in category_links]:
                    category_links.append((text, full_url))
        
        return category_links, soup
        
    except requests.RequestException as e:
        err(f"Failed to fetch {url}: {e}")

def display_menu(items, title):
    """Display a numbered menu and return user's selection."""
    print(f"\n  {Style.BRIGHT if HAS_COLOR else ''}{title}{Style.RESET_ALL if HAS_COLOR else ''}\n")
    for i, (name, _) in enumerate(items, 1):
        print(f"  {i}. {name}")
    print()
    
    while True:
        try:
            choice = int(input("Enter number: ").strip())
            if 1 <= choice <= len(items):
                return items[choice - 1]
            print("Invalid choice. Try again.")
        except ValueError:
            print("Please enter a valid number.")

def download_pdf(pdf_info, save_dir, headers):
    """Download a single PDF file."""
    name, url = pdf_info
    
    # Clean filename
    filename = name.replace(' ', '_').replace('/', '_').replace('\\', '_')
    if not filename.lower().endswith('.pdf'):
        filename += '.pdf'
    
    filepath = save_dir / filename
    
    step(f"Downloading: {name}")
    
    try:
        response = requests.get(url, headers=headers, timeout=60, stream=True)
        response.raise_for_status()
        
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        size = filepath.stat().st_size
        if size < 1000:
            filepath.unlink()
            return False, f"File too small ({size} bytes) - likely not a valid PDF"
        
        ok(f"Saved: {filename} ({size:,} bytes)")
        return True, filepath
        
    except requests.RequestException as e:
        return False, str(e)

def download_all_pdfs(url, save_dir, headers, delay=1):
    """Download all PDFs from a given URL page."""
    step(f"Scanning for PDFs at: {url}")
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        pdf_links = []
        
        # Method 1: Direct PDF links
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '.pdf' in href.lower():
                full_url = urljoin(url, href)
                text = link.get_text(strip=True) or href.split('/')[-1]
                pdf_link = (text, full_url)
                if pdf_link not in pdf_links:
                    pdf_links.append(pdf_link)
        
        # Method 2: Links that might redirect to PDFs
        for link in soup.find_all('a', href=True):
            href = link['href']
            text = link.get_text(strip=True)
            
            # Common patterns for past paper download links
            if any(x in href.lower() for x in ['download', 'paper', 'qp', 'ms', 'question', 'marking']):
                if '.pdf' in href.lower() or '/download/' in href.lower() or '/papers/' in href.lower():
                    full_url = urljoin(url, href)
                    if full_url not in [p[1] for p in pdf_links]:
                        pdf_links.append((text or href.split('/')[-1], full_url))
        
        # Method 3: Detect links to another page with PDFs
        download_page_links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            text = link.get_text(strip=True)
            
            if any(x in href.lower() for x in ['year', 'variant', 'variant', 'paper', 'download']):
                if 'http' in href or href.startswith('/'):
                    full_url = urljoin(url, href)
                    if full_url not in [p[1] for p in download_page_links]:
                        text = text.strip() if text.strip() else href.split('/')[-1]
                        download_page_links.append((text, full_url))
        
        print(f"  Found {len(pdf_links)} direct PDF links and {len(download_page_links)} download pages")
        
        # Download direct PDFs
        downloaded = []
        failed = []
        
        for pdf_info in pdf_links:
            result, msg = download_pdf(pdf_info, save_dir, headers)
            if result:
                downloaded.append(msg)
            else:
                failed.append((pdf_info[0], msg))
            time.sleep(delay)
        
        # Check download pages for more PDFs
        for page_name, page_url in download_page_links[:5]:  # Limit to avoid too many requests
            step(f"Checking download page: {page_name}")
            try:
                response = requests.get(page_url, headers=headers, timeout=30)
                page_soup = BeautifulSoup(response.text, 'html.parser')
                
                for link in page_soup.find_all('a', href=True):
                    href = link['href']
                    if '.pdf' in href.lower():
                        full_url = urljoin(page_url, href)
                        text = link.get_text(strip=True) or href.split('/')[-1]
                        pdf_info = (text, full_url)
                        
                        result, msg = download_pdf(pdf_info, save_dir, headers)
                        if result:
                            downloaded.append(msg)
                        else:
                            failed.append((text, msg))
                        time.sleep(delay)
                        
            except Exception as e:
                step(f"Could not check page: {e}")
        
        return downloaded, failed
        
    except requests.RequestException as e:
        return [], [(url, str(e))]

def main():
    clear()
    print_banner()
    
    if HAS_COLOR:
        print(f"  {Style.DIM}Downloads past papers from PapaCambridge{Style.RESET_ALL}")
    else:
        print("  Downloads past papers from PapaCambridge")
    print()
    
    # Ask for exam board
    categories = [
        ("IGCSE / O-Level", "https://papacambridge.com/igcse/"),
        ("AS & A-Level", "https://papacambridge.com/a-level/"),
        ("GCSE", "https://papacambridge.com/gcse/"),
        ("O-Level (5026)", "https://papacambridge.com/o-level/"),
    ]
    
    divider()
    chosen_board, board_url = display_menu(categories, "Select Exam Board")
    ok(f"Selected: {chosen_board}")
    
    # Get subjects
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    divider()
    step("Fetching subject list...")
    
    subjects, _ = get_category_links(board_url, headers)
    
    if not subjects:
        err("No subjects found. The website structure may have changed.")
    
    # Let user select subject
    divider()
    chosen_subject, subject_url = display_menu(subjects, "Select Subject")
    ok(f"Selected: {chosen_subject}")
    
    # Create folder for this subject
    folder_name = f"past_papers_{chosen_subject.replace(' ', '_').replace('&', 'and')}"
    save_dir = PAPERS_DIR / folder_name
    save_dir.mkdir(exist_ok=True)
    
    # Fetch available years/variants
    divider()
    step("Fetching available years and variants...")
    
    variants, _ = get_category_links(subject_url, headers)
    
    # Download PDFs
    divider()
    print()
    
    all_downloaded = []
    all_failed = []
    
    if variants:
        # Download from each variant/year page
        for variant_name, variant_url in variants:
            print(f"\n  {Style.BRIGHT if HAS_COLOR else ''}--- {variant_name} ---{Style.RESET_ALL if HAS_COLOR else ''}\n")
            downloaded, failed = download_all_pdfs(variant_url, save_dir, headers)
            all_downloaded.extend(downloaded)
            all_failed.extend(failed)
            
            # Limit to avoid too many requests
            if len(all_downloaded) >= 50:
                step("Reached download limit (50 files). Stopping...")
                break
    else:
        # Try downloading directly from subject page
        downloaded, failed = download_all_pdfs(subject_url, save_dir, headers)
        all_downloaded.extend(downloaded)
        all_failed.extend(failed)
    
    # Summary
    divider()
    print()
    
    if HAS_COLOR:
        print(f"  {Style.BRIGHT}DOWNLOAD COMPLETE{Style.RESET_ALL}\n")
    else:
        print("  DOWNLOAD COMPLETE\n")
    
    ok(f"Files downloaded: {len(all_downloaded)}")
    if all_failed:
        print(f"  {Fore.RED}Failed to download: {len(all_failed)}{Style.RESET_ALL if HAS_COLOR else ''}")
        for name, error in all_failed[:10]:
            print(f"    - {name}: {error[:50]}")
    
    print(f"\n  Files saved to: {save_dir.absolute()}")
    print()

if __name__ == "__main__":
    main()
</contents>