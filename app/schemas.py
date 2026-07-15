# app/schemas.py
from pydantic import BaseModel
from typing import List, Optional

class ChatRequest(BaseModel):
    model: Optional[str] = None  # e.g. "ollama/llama3.2:3b" -- falls back to the configured default if omitted
    conversation_id: str  # New: group messages by ID
    system_prompt: Optional[str] = "You are a helpful AI assistant." # New: AI persona
    messages: List[dict]