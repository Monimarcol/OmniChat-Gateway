# app/main.py
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from .database import get_db, ChatMessage
from .schemas import ChatRequest
from .services import LLMService

app = FastAPI()

@app.post("/chat")
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    # 1. Save user message with conversation_id
    user_msg = ChatMessage(
        conversation_id=request.conversation_id, 
        role="user", 
        content=request.messages[-1]["content"]
    )
    db.add(user_msg)
    
    # 2. Call service with system prompt
    response_text = await LLMService.generate_response(request.messages, request.system_prompt)

    # 3. Save assistant response with same conversation_id
    ai_msg = ChatMessage(
        conversation_id=request.conversation_id, 
        role="assistant", 
        content=response_text
    )
    db.add(ai_msg)
    db.commit()

    return {"response": response_text}

@app.get("/history/{conversation_id}")
async def get_history(conversation_id: str, db: Session = Depends(get_db)):
    # Query the database for all messages with this conversation_id
    messages = db.query(ChatMessage).filter(ChatMessage.conversation_id == conversation_id).all()
    
    # Return them in a format the UI can understand
    return [{"role": m.role, "content": m.content} for m in messages]