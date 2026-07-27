import os
import requests
from typing import List, Tuple, Dict, Any, Optional
from app.config import settings
from app.rag.chunker import Chunk
from app.schemas.api_models import Citation, ChatResponse

REFUSAL_MESSAGE = "I am sorry, but the requested information is unavailable in the provided textbook knowledge base."

class RAGGenerator:
    def __init__(self):
        self.openai_key = settings.OPENAI_API_KEY
        self.gemini_key = settings.GEMINI_API_KEY

    def _call_openai(self, system_prompt: str, user_prompt: str) -> str:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openai_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.1
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    def _get_gemini_key(self) -> str:
        key = self.gemini_key or os.getenv("GEMINI_API_KEY", "") or getattr(settings, "GEMINI_API_KEY", "")
        if not key:
            try:
                import streamlit as st
                key = st.secrets.get("GEMINI_API_KEY", "")
            except Exception:
                pass
        return key

    def _call_gemini(self, system_prompt: str, user_prompt: str, api_key: str = "") -> str:
        key = api_key or self._get_gemini_key()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": f"{system_prompt}\n\n{user_prompt}"}
                    ]
                }
            ],
            "generationConfig": {"temperature": 0.1}
        }
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"]

    def _fallback_extractive_answer(self, query: str, context_chunks: List[Tuple[Chunk, float]]) -> str:
        """
        Extractive grounded answer synthesizer when no external cloud LLM API key is present.
        Extracts key sentences matching the query from the top chunks.
        """
        query_words = set(query.lower().split())
        matched_sentences = []

        for chunk, score in context_chunks:
            sentences = chunk.text.split(". ")
            for s in sentences:
                s_clean = s.strip()
                if not s_clean:
                    continue
                overlap = len(set(s_clean.lower().split()).intersection(query_words))
                if overlap >= 2 or len(sentences) == 1:
                    matched_sentences.append(s_clean)
                    if len(matched_sentences) >= 4:
                        break
            if len(matched_sentences) >= 4:
                break

        if not matched_sentences:
            matched_sentences = [context_chunks[0][0].text[:300] + "..."]

        summary = " ".join(matched_sentences)
        return f"Based on the textbook contents: {summary}"

    def generate_response(
        self,
        query: str,
        context_chunks: List[Tuple[Chunk, float]],
        conversation_history: str = "",
        session_id: str = "default",
        target_language: str = "English",
        **kwargs
    ) -> ChatResponse:
        # Check if context chunks exist or are too weak
        if not context_chunks:
            return ChatResponse(
                answer=REFUSAL_MESSAGE,
                is_grounded=False,
                citations=[],
                session_id=session_id
            )

        # Build Citations list
        citations: List[Citation] = []
        context_blocks = []
        
        for idx, (chunk, score) in enumerate(context_chunks):
            citation = Citation(
                book_name=chunk.book_name,
                page_number=chunk.page_number,
                standard=chunk.standard,
                subject=chunk.subject,
                relevant_text=chunk.text,
                score=round(score, 4)
            )
            citations.append(citation)
            context_blocks.append(
                f"[Source {idx+1}: {chunk.book_name} | {chunk.standard} {chunk.subject} | Page {chunk.page_number}]\n{chunk.text}"
            )

        context_str = "\n\n".join(context_blocks)

        lang_instruction = "Write your answer in clear, fluent ENGLISH."
        if target_language == "Gujarati":
            lang_instruction = "Write your answer in clear GUJARATI UNICODE (ગુજરાતી) script."
        elif target_language == "Same as Question":
            lang_instruction = "Write your answer in the same language as the user's question."

        system_prompt = (
            "You are an expert AI tutor for Gujarat State School Board (GSSTB) textbooks.\n"
            "STRICT RULES:\n"
            "1. Answer the user question STRICTLY using only the provided textbook context snippets.\n"
            f"2. {lang_instruction} Even if the textbook snippets are in Gujarati or contain legacy encoding symbols, translate the underlying facts and provide a clean, complete response in the requested target language.\n"
            "3. If the answer CANNOT be directly found in or inferred from the provided snippets, respond EXACTLY with:\n"
            f"'{REFUSAL_MESSAGE}'\n"
            "4. Do NOT use any external or prior knowledge outside the context snippets.\n"
            "5. Cite the textbook name and page number when stating facts."
        )

        user_prompt = f"Previous Conversation Context:\n{conversation_history}\n\nTextbook Context Snippets:\n{context_str}\n\nUser Question: {query}\n\nAnswer:"

        answer = ""
        is_grounded = True

        # Try API providers if keys are present
        if self.openai_key:
            try:
                answer = self._call_openai(system_prompt, user_prompt)
            except Exception as e:
                print(f"[Generator] OpenAI call failed: {e}")

        gemini_key = self._get_gemini_key()
        if not answer and gemini_key:
            try:
                answer = self._call_gemini(system_prompt, user_prompt, api_key=gemini_key)
            except Exception as e:
                print(f"[Generator] Gemini call failed: {e}")

        # Local Extractive Fallback
        if not answer:
            answer = self._fallback_extractive_answer(query, context_chunks)

        if REFUSAL_MESSAGE.lower() in answer.lower():
            is_grounded = False
            citations = []

        return ChatResponse(
            answer=answer.strip(),
            is_grounded=is_grounded,
            citations=citations if is_grounded else [],
            session_id=session_id
        )
