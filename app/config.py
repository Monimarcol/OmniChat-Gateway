# app/config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    MODEL_NAME: str = os.getenv("MODEL_NAME", "ollama/llama3")
    API_BASE: str = os.getenv("API_BASE", "http://127.0.0.1:11434")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./chat_history.db")

settings = Settings()