from typing import List, Dict, Any

class ConversationMemory:
    def __init__(self, max_history: int = 6):
        self.max_history = max_history
        # Session ID -> List of {"role": "user"|"assistant", "content": str}
        self.sessions: Dict[str, List[Dict[str, str]]] = {}

    def add_message(self, session_id: str, role: str, content: str):
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        
        self.sessions[session_id].append({"role": role, "content": content})
        
        # Keep recent context window
        if len(self.sessions[session_id]) > self.max_history * 2:
            self.sessions[session_id] = self.sessions[session_id][-self.max_history * 2:]

    def get_history(self, session_id: str) -> List[Dict[str, str]]:
        return self.sessions.get(session_id, [])

    def format_history_for_prompt(self, session_id: str) -> str:
        history = self.get_history(session_id)
        if not history:
            return ""
        
        formatted = []
        for msg in history[-4:]: # Use last 2 exchanges
            role = "User" if msg["role"] == "user" else "Assistant"
            formatted.append(f"{role}: {msg['content']}")
        return "\n".join(formatted)

    def clear(self, session_id: str):
        if session_id in self.sessions:
            self.sessions[session_id] = []
