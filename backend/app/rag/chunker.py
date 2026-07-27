from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.rag.parser import PageContent
from app.config import settings

class Chunk:
    def __init__(self, chunk_id: str, text: str, book_name: str, page_number: int, standard: str, subject: str):
        self.chunk_id = chunk_id
        self.text = text
        self.book_name = book_name
        self.page_number = page_number
        self.standard = standard
        self.subject = subject

    def to_metadata(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "book_name": self.book_name,
            "page_number": int(self.page_number),
            "standard": self.standard,
            "subject": self.subject
        }


class MetadataPreservingChunker:
    def __init__(self, chunk_size: int = settings.CHUNK_SIZE, chunk_overlap: int = settings.CHUNK_OVERLAP):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

    def chunk_pages(self, pages: List[PageContent]) -> List[Chunk]:
        all_chunks: List[Chunk] = []
        chunk_counter = 0

        for page in pages:
            if not page.text.strip():
                continue

            sub_chunks = self.splitter.split_text(page.text)
            for sub_idx, sub_text in enumerate(sub_chunks):
                chunk_counter += 1
                clean_chunk_id = f"{page.book_name}_p{page.page_number}_c{sub_idx+1}_{chunk_counter}"
                all_chunks.append(Chunk(
                    chunk_id=clean_chunk_id,
                    text=sub_text.strip(),
                    book_name=page.book_name,
                    page_number=page.page_number,
                    standard=page.standard,
                    subject=page.subject
                ))

        return all_chunks
