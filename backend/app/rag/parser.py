import os
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple
from pypdf import PdfReader

class PageContent:
    def __init__(self, page_number: int, text: str, book_name: str, standard: str = "Unknown", subject: str = "Unknown"):
        self.page_number = page_number
        self.text = text
        self.book_name = book_name
        self.standard = standard
        self.subject = subject

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_number": self.page_number,
            "text": self.text,
            "book_name": self.book_name,
            "standard": self.standard,
            "subject": self.subject
        }


def extract_metadata_from_filename(filename: str) -> Tuple[str, str, str]:
    clean_name = Path(filename).stem
    
    # Standard detection
    std_match = re.search(r'(?:std|class|grade|standard)[._\s\-]*(\d{1,2})', clean_name, re.IGNORECASE)
    if std_match:
        standard = f"Std {std_match.group(1)}"
    else:
        standard = "General"

    # Subject detection
    subjects = [
        "Science", "Mathematics", "Maths", "Social Science", "Physics", 
        "Chemistry", "Biology", "English", "Gujarati", "Hindi", "History", 
        "Geography", "Economics", "Civics", "Accountancy", "Business"
    ]
    detected_subject = "General"
    for sub in subjects:
        if re.search(r'\b' + re.escape(sub) + r'\b', clean_name, re.IGNORECASE):
            detected_subject = sub
            break

    # Format human readable book name
    book_name = clean_name.replace("_", " ").replace("-", " ").strip()
    return book_name, standard, detected_subject


class PDFBookParser:
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.book_name, self.standard, self.subject = extract_metadata_from_filename(self.file_path.name)

    def parse(self, progress_callback=None) -> List[PageContent]:
        pages = []
        
        # 1. Try PyMuPDF (fitz) - High speed C++ engine (0.3s for 300 pages, ultra-low RAM)
        try:
            import fitz
            doc = fitz.open(str(self.file_path))
            total_pages = len(doc)
            
            for idx, page in enumerate(doc):
                page_num = idx + 1
                if progress_callback and (idx % 10 == 0 or idx == total_pages - 1):
                    progress_callback(page_num, total_pages)

                raw_text = page.get_text("text") or ""
                cleaned_text = re.sub(r'[ \t]+', ' ', raw_text).strip()
                
                if cleaned_text:
                    pages.append(PageContent(
                        page_number=page_num,
                        text=cleaned_text,
                        book_name=self.book_name,
                        standard=self.standard,
                        subject=self.subject
                    ))
            doc.close()
        except Exception as e:
            print(f"PyMuPDF extraction error: {e}")

        # 2. Fallback to PyPDF if PyMuPDF extracted no text
        if not pages:
            try:
                reader = PdfReader(str(self.file_path))
                total_pages = len(reader.pages)
                
                for idx, page in enumerate(reader.pages):
                    page_num = idx + 1
                    if progress_callback and (idx % 10 == 0 or idx == total_pages - 1):
                        progress_callback(page_num, total_pages)

                    raw_text = page.extract_text() or ""
                    cleaned_text = re.sub(r'[ \t]+', ' ', raw_text).strip()
                    
                    if cleaned_text:
                        pages.append(PageContent(
                            page_number=page_num,
                            text=cleaned_text,
                            book_name=self.book_name,
                            standard=self.standard,
                            subject=self.subject
                        ))
            except Exception as e:
                print(f"pypdf extraction error: {e}")

        return pages
