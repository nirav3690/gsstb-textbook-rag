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
    """
    Extracts book_name, standard (e.g. Std 9..12), and subject from filename or title.
    Examples: 'Std_10_Science_GSSTB.pdf', 'Class_11_Physics_Ch1.pdf'
    """
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
        try:
            reader = PdfReader(str(self.file_path))
            total_pages = len(reader.pages)
            
            for idx, page in enumerate(reader.pages):
                page_num = idx + 1
                if progress_callback and (idx % 5 == 0 or idx == total_pages - 1):
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

        # Fallback to pdfplumber if pypdf extracted no text
        if not pages:
            try:
                import pdfplumber
                with pdfplumber.open(str(self.file_path)) as pdf:
                    total_pages = len(pdf.pages)
                    for idx, page in enumerate(pdf.pages):
                        page_num = idx + 1
                        if progress_callback and (idx % 5 == 0 or idx == total_pages - 1):
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
                print(f"pdfplumber extraction error: {e}")

        return pages
