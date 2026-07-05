# app/router.py
from litellm import completion

async def route_chat_request(model_name: str, messages: list):
    try:
        # Connect to your local inference engine (e.g., Ollama)
        response = completion(
            model=model_name,
            messages=messages,
            api_base="http://localhost:11434"
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"