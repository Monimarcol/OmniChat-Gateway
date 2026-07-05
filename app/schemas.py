# app/schemas.py
from pydantic import BaseModel
from typing import List, Optional

class ChatRequest(BaseModel):
    model: str
    conversation_id: str  # New: group messages by ID
    system_prompt: Optional[str] = "You are a helpful AI assistant." # New: AI persona
    messages: List[dict]