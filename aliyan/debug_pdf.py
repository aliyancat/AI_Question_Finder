import sys
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    sys.exit("Please run: pip install PyMuPDF")

PAPERS_DIR = Path("past_papers")

def debug_pdfs():
    if not PAPERS_DIR.exists():
        print(f"Error: Directory '{PAPERS_DIR}' not found.")
        return

    pdf_files = list(PAPERS_DIR.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDFs found in '{PAPERS_DIR}'.")
        return

    for pdf in sorted(pdf_files):
        print(f"\n" + "="*50)
        print(f"📄 Reading: {pdf.name}")
        print("="*50 + "\n")
        
        doc = fitz.open(str(pdf))
        full_text = ""
        
        for page_num, page in enumerate(doc, start=1):
            text = page.get_text()
            full_text += f"\n--- Page {page_num} ---\n{text}"
            
        doc.close()
        
        # Save to a debug file for easy viewing
        debug_file = Path(f"debug_{pdf.stem}.txt")
        debug_file.write_text(full_text, encoding="utf-8")
        
        print(f"✅ Extracted {len(full_text)} characters.")
        print(f"💾 Full text saved to: {debug_file.absolute()}")
        
        # Print a small preview of the first 500 characters
        print("\n--- PREVIEW (First 500 characters) ---")
        print(full_text[:500])
        print("...\n")

if __name__ == "__main__":
    debug_pdfs()
