import os
from pathlib import Path
from pypdf import PdfWriter

def create_sample_textbook():
    sample_dir = Path(__file__).parent
    sample_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = sample_dir / "Std_10_Science_GSSTB_Sample.pdf"

    writer = PdfWriter()

    # Page 1: Chapter 1 - Chemical Reactions
    writer.add_blank_page(width=612, height=792)
    
    # Page 2: Chapter 2 - Newton's Laws of Motion
    writer.add_blank_page(width=612, height=792)

    # Note: For text extraction testing, we can write a plain PDF page with text stream
    # or create a text-filled PDF with pypdf
    print(f"Sample PDF target path: {pdf_path}")

if __name__ == "__main__":
    create_sample_textbook()
