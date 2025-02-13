import os
from google import genai
from dotenv import load_dotenv # type: ignore

load_dotenv()

gemKey = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=gemKey)

def send_message(message, chat):
    print(f"Received message: {message}")
    response = chat.send_message(message)
    return response
