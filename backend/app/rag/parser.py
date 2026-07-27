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


LEGACY_GUJARATI_MAP = {
    # Vowels & Consonants
    'Â': 'આ', 'Ã': 'ઇ', 'Ä': 'ઈ', 'Å': 'ઉ', 'Æ': 'ઊ', 'Ç': 'ઋ', 'È': 'એ', 'É': 'ઐ', 'Ê': 'ઓ', 'Ë': 'ઔ',
    'Ì': 'ક', 'Í': 'ખ', 'Î': 'ગ', 'Ï': 'ઘ', 'Ð': 'ચ', 'Ñ': 'છ', 'Ò': 'જ', 'Ó': 'ઝ', 'Ô': 'ટ', 'Õ': 'ઠ',
    'Ö': 'ડ', '×': 'ઢ', 'Ø': 'ણ', 'Ù': 'ત', 'Ú': 'થ', 'Û': 'દ', 'Ü': 'ધ', 'Ý': 'ન', 'Þ': 'પ', 'ß': 'ફ',
    'à': 'બ', 'á': 'ભ', 'â': 'મ', 'ã': 'ય', 'ä': 'ર', 'å': 'લ', 'æ': 'વ', 'ç': 'શ', 'è': 'ષ', 'é': 'સ',
    'ê': 'હ', 'ë': 'ળ', 'ì': 'ક્ષ', 'í': 'જ્ઞ', '¿': 'જ', 'À': 'ગ',
    # Matras
    'î': 'ા', 'ï': 'ી', 'ð': 'ુ', 'ñ': 'ૂ', 'ò': 'ૃ', 'ó': 'ે', 'ô': 'ૈ', 'õ': 'ો', 'ö': 'ૌ', '÷': 'ં',
    'ø': 'ઃ', 'ù': '્', '±': 'ા', 'º': 'ુ', '»': 'ૂ', '«': 'ે', '¬': 'ો', 'ˆ': 'ં', '˜': 'ં', '‰': 'ં',
    'Ï0': 'ધો', 'Î0': 'ગો', 'Ò0': 'જો', 'Ì0': 'કો', 'é0': 'સો', 'â0': 'મો', 'Ù0': 'તો'
}

def fix_legacy_gujarati_text(text: str) -> str:
    """
    Detects and converts legacy Gujarati font encodings (Gopika/Harikrishna/Akruti)
    to clean, searchable Gujarati Unicode characters.
    """
    if not text:
        return text

    # Check if text contains high density of garbled legacy characters
    legacy_char_count = sum(1 for c in text if c in LEGACY_GUJARATI_MAP or ord(c) > 160)
    if legacy_char_count / max(1, len(text)) < 0.05:
        return text # Standard English or already Unicode text

    # Handle pre-consonant 'i' matra (fî / fi / fï)
    text = re.sub(r'f[iîï]([\u00A0-\u00FF|a-zA-Z])', r'\1િ', text)

    # Replace character mappings
    converted = []
    i = 0
    while i < len(text):
        # Two character match check
        if i + 1 < len(text) and text[i:i+2] in LEGACY_GUJARATI_MAP:
            converted.append(LEGACY_GUJARATI_MAP[text[i:i+2]])
            i += 2
        elif text[i] in LEGACY_GUJARATI_MAP:
            converted.append(LEGACY_GUJARATI_MAP[text[i]])
            i += 1
        else:
            converted.append(text[i])
            i += 1

    result = "".join(converted)
    # Clean up non-printable control characters
    result = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', result)
    return result


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
        "Geography", "Economics", "Civics", "Accountancy", "Business", "GruhVigyan"
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
        
        # 1. Try PyMuPDF (fitz) - High speed C++ engine
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
                cleaned_text = fix_legacy_gujarati_text(cleaned_text)
                
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
                    cleaned_text = fix_legacy_gujarati_text(cleaned_text)
                    
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
