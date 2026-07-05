import os
from google import genai
from dotenv import load_dotenv

# Automatically finds and loads the local .env file
load_dotenv()

# Initialize the modern client (it automatically picks up GEMINI_API_KEY from os.environ)
client = genai.Client()

response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents=(
        "You are an AI for a civic complaint system. "
        "A citizen says: 'There is a huge pothole on MG Road.' "
        "Classify this in one sentence."
    )
)

print("Gemini says:", response.text)
print("✅ Gemini is working!")