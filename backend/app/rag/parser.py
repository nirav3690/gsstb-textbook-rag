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


def _is_garbled_text(text: str) -> bool:
    """
    Detect if extracted text is garbled (legacy font encoding issue).
    Garbled text from legacy Gujarati fonts has a high ratio of extended ASCII symbols
    (Latin-1 Supplement: U+0080 to U+00FF, e.g. ï, Á, fî, ¿, Õ, Ï, ò, Ì, ÷, œ, ê, ›, ÿ).
    """
    if not text or len(text) < 20:
        return False
    
    total = len(text.replace(' ', '').replace('\n', ''))
    if total == 0:
        return False

    # Count extended ASCII / Latin-1 Supplement characters and legacy ligatures (fi, fl, ‹, ›)
    extended_ascii_count = sum(
        1 for c in text 
        if ('\u0080' <= c <= '\u00FF') or (c in '¿ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞßàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ‹›')
    )
    
    ratio = extended_ascii_count / total
    # If more than 4% of the text consists of extended ASCII symbols, it's garbled legacy font
    return ratio > 0.04


class PDFBookParser:
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.book_name, self.standard, self.subject = extract_metadata_from_filename(self.file_path.name)
        self.extraction_method = "unknown"
        self.is_legacy_font = False

    def _extract_with_fitz(self, progress_callback=None) -> List[PageContent]:
        """Primary: PyMuPDF C++ engine text extraction."""
        pages = []
        try:
            import fitz
            doc = fitz.open(str(self.file_path))
            total_pages = len(doc)
            
            for idx, page in enumerate(doc):
                page_num = idx + 1
                if progress_callback and (idx % 10 == 0 or idx == total_pages - 1):
                    progress_callback(page_num, total_pages, "Extracting text (PyMuPDF)")

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
        return pages

    def _extract_with_pypdf(self, progress_callback=None) -> List[PageContent]:
        """Fallback: pypdf text extraction."""
        pages = []
        try:
            reader = PdfReader(str(self.file_path))
            total_pages = len(reader.pages)
            
            for idx, page in enumerate(reader.pages):
                page_num = idx + 1
                if progress_callback and (idx % 10 == 0 or idx == total_pages - 1):
                    progress_callback(page_num, total_pages, "Extracting text (PyPDF)")

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

    def _extract_with_ocr(self, progress_callback=None) -> List[PageContent]:
        """
        OCR fallback for legacy Gujarati font PDFs.
        Renders each page as a high-res image, then uses Gemini API for OCR.
        """
        gemini_key = os.getenv("GEMINI_API_KEY", "") or getattr(settings, "GEMINI_API_KEY", "")
        if not gemini_key:
            try:
                import streamlit as st
                gemini_key = st.secrets.get("GEMINI_API_KEY", "")
            except Exception:
                pass
        
        if not gemini_key:
            print("OCR skipped: No GEMINI_API_KEY found in env, settings, or Streamlit Secrets")
            return pages
        
        try:
            import fitz
            import requests
            import base64
            
            doc = fitz.open(str(self.file_path))
            total_pages = len(doc)
            
            for idx, page in enumerate(doc):
                page_num = idx + 1
                if progress_callback and (idx % 2 == 0 or idx == total_pages - 1):
                    progress_callback(page_num, total_pages, "OCR via Gemini Vision")
                
                # Render page as image (150 DPI for good quality, manageable size)
                mat = fitz.Matrix(150 / 72, 150 / 72)
                pix = page.get_pixmap(matrix=mat)
                img_bytes = pix.tobytes("png")
                img_b64 = base64.b64encode(img_bytes).decode("utf-8")
                
                # Call Gemini Vision API for OCR
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}"
                payload = {
                    "contents": [{
                        "parts": [
                            {"text": "Extract ALL text from this textbook page image. Return ONLY the extracted text content, preserving paragraph structure. If the text is in Gujarati, return it in Gujarati Unicode. Do not add any commentary or formatting."},
                            {"inline_data": {"mime_type": "image/png", "data": img_b64}}
                        ]
                    }],
                    "generationConfig": {"temperature": 0.0, "maxOutputTokens": 4096}
                }
                
                try:
                    resp = requests.post(url, json=payload, timeout=60)
                    resp.raise_for_status()
                    result = resp.json()
                    ocr_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                    
                    if ocr_text and len(ocr_text) > 10:
                        pages.append(PageContent(
                            page_number=page_num,
                            text=ocr_text,
                            book_name=self.book_name,
                            standard=self.standard,
                            subject=self.subject
                        ))
                except Exception as e:
                    print(f"OCR error on page {page_num}: {e}")
                    continue
            
            doc.close()
        except Exception as e:
            print(f"OCR pipeline error: {e}")
        
        return pages

    def parse(self, progress_callback=None) -> List[PageContent]:
        """
        Smart multi-strategy PDF text extraction:
        1. Try PyMuPDF text extraction (fast, low memory)
        2. If garbled (legacy font), try OCR via Gemini Vision API
        3. Fallback to pypdf
        """
        # Strategy 1: PyMuPDF
        pages = self._extract_with_fitz(progress_callback)
        self.extraction_method = "PyMuPDF"
        
        # Check if text is garbled (legacy Gujarati font)
        if pages:
            sample_pages = pages[:5]
            garbled_count = sum(1 for p in sample_pages if _is_garbled_text(p.text))
            
            if garbled_count >= len(sample_pages) * 0.5:
                self.is_legacy_font = True
                print(f"[Parser] Detected legacy Gujarati font in '{self.book_name}'. Attempting OCR...")
                
                # Strategy 2: OCR via Gemini Vision
                ocr_pages = self._extract_with_ocr(progress_callback)
                if ocr_pages:
                    self.extraction_method = "Gemini Vision OCR"
                    return ocr_pages
                else:
                    # Return garbled text with a warning prefix
                    print(f"[Parser] OCR failed or no API key. Returning raw extracted text.")
                    self.extraction_method = "PyMuPDF (legacy font - may contain encoding artifacts)"
        
        # Strategy 3: Fallback to pypdf if PyMuPDF got nothing
        if not pages:
            pages = self._extract_with_pypdf(progress_callback)
            self.extraction_method = "PyPDF"
        
        return pages
