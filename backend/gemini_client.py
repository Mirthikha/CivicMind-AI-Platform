from google import genai
from google.genai import types
import os
from dotenv import load_dotenv

load_dotenv()

# Create ONE client that all agents will share
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Model name - using latest Gemini 2.5 Flash
MODEL_NAME = "gemini-2.5-flash"

def generate_text(prompt: str) -> str:
    """
    Send a text prompt to Gemini, get text back.
    Used by: classification, intelligence, explainability agents
    """
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )
    return response.text

def generate_with_image(prompt: str, image_bytes: bytes) -> str:
    """
    Send text + image to Gemini, get text back.
    Used by: intake agent when citizen uploads a photo
    """
    import PIL.Image
    import io
    
    image = PIL.Image.open(io.BytesIO(image_bytes))
    
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[prompt, image]
    )
    return response.text