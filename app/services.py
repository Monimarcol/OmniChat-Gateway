# app/services.py
from litellm import completion
from .config import settings

class LLMService:
    @staticmethod
    async def generate_response(messages: list, system_prompt: str):
        # Insert system prompt at the start
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        
        response = completion(
            model=settings.MODEL_NAME,
            messages=full_messages,
            api_base=settings.API_BASE
        )
        return response.choices[0].message.content