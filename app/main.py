# app/main.py
from dataclasses import asdict

from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .database import get_db, ChatMessage
from .hardware import get_hardware_profile
from .model_catalog import CATALOG
from .ollama_client import is_pulled, pull_model
from .recommender import recommend_models
from .schemas import ChatRequest
from .services import LLMService

app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/hardware")
async def hardware(force_refresh: bool = False):
    return asdict(get_hardware_profile(force_refresh=force_refresh))

@app.get("/models")
async def models():
    return [
        {
            "id": m.id,
            "ollama_tag": m.ollama_tag,
            "display_name": m.display_name,
            "min_ram_gb": m.min_ram_gb,
            "param_count": m.param_count,
            "tags": m.tags,
            "strengths": m.strengths,
            "limitations": m.limitations,
        }
        for m in CATALOG
    ]

class RecommendRequest(BaseModel):
    description: str

@app.post("/models/recommend")
async def models_recommend(request: RecommendRequest):
    hardware = get_hardware_profile()
    recs = recommend_models(hardware, request.description)
    return [
        {
            "id": r.model.id,
            "ollama_tag": r.model.ollama_tag,
            "display_name": r.model.display_name,
            "rationale": r.rationale,
        }
        for r in recs
    ]

@app.post("/models/{model_id}/ensure")
async def models_ensure(model_id: str):
    model = next((m for m in CATALOG if m.id == model_id), None)
    if model is None:
        raise HTTPException(status_code=404, detail=f"Unknown model id: {model_id}")
    if not is_pulled(model.ollama_tag):
        pull_model(model.ollama_tag)
    return {"ollama_tag": model.ollama_tag, "pulled": True}

@app.post("/chat")
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    # 1. Save user message with conversation_id
    user_msg = ChatMessage(
        conversation_id=request.conversation_id,
        role="user",
        content=request.messages[-1]["content"]
    )
    db.add(user_msg)

    # 2. Call service with system prompt and the caller's selected model, if any
    response_text = await LLMService.generate_response(
        request.messages, request.system_prompt, model=request.model
    )

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
