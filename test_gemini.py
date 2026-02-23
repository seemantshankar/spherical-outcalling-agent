import os
from google import genai
try:
    client = genai.Client()
    print("Gemini client initialized")
except Exception as e:
    print(f"Failed: {e}")
