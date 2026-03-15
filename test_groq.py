import asyncio
from backend.utils.llm_client import LLMClient
from backend.config import settings

def main():
    print(f"Testing Groq model: {settings.groq_model}")
    client = LLMClient()
    response = client.chat_groq([{"role": "user", "content": "Say hello!"}])
    print("Response:", response)

main()
