import re
from PyPDF2 import PdfReader
    
def extract_text_from_pdf(pdf_path):
    """
    Improved PDF text extraction:
    - Tries pdfplumber with better settings (x/y tolerance)
    - Falls back to PyPDF2
    - Falls back to OCR (high DPI, better layout config)
    - Post-processes to remove headers/footers, fix hyphens, normalize whitespace
    """

    """
    Simple PDF text extraction using PyPDF2.
    Post-processes to remove headers/footers, fix hyphens, normalize whitespace.
    """
    try:
        # Accept both file path (str) and file-like object (BytesIO)
        reader = PdfReader(pdf_path)
        text = "\n".join([page.extract_text() or "" for page in reader.pages])
        if text and len(text.strip()) > 20:
            return postprocess_pdf_text(text)
        else:
            print(f"No valid text extracted from {pdf_path}")
            return ""
    except Exception as e:
        print(f"[PyPDF2] Extraction failed for {pdf_path}: {e}")
        return ""

def postprocess_pdf_text(text):
    """
    Post-process extracted PDF text:
    - Remove repeated headers/footers
    - Merge hyphenated words
    - Normalize whitespace
    - Remove non-UTF8 chars
    """
    # Remove repeated lines (headers/footers)
    lines = text.splitlines()
    line_counts = {}
    for line in lines:
        line_counts[line] = line_counts.get(line, 0) + 1
    cleaned_lines = [line for line in lines if line_counts[line] < 0.5 * len(lines)]
    text = "\n".join(cleaned_lines)
    # Merge hyphenated words at line breaks
    text = re.sub(r"(\w+)-\n(\w+)", r"\1\2", text)
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)
    # Remove non-UTF8 chars
    text = text.encode("utf-8", errors="ignore").decode("utf-8")
    return text.strip()



def clean_text(text):
    text = re.sub(r"\n+", " ", text)
    text = re.sub(r"[^a-zA-Z0-9\s\-]", "", text)  # Keep only clean characters
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()

def chunk_text(text, chunk_size=1000, overlap=100):
    """
    Split text into chunks of chunk_size with optional overlap.
    Returns a list of text chunks.
    """
    chunks = []
    start = 0
    text_length = len(text)
    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


