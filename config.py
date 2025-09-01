import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Gemini API Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

QUIZ_DATA_FILE = os.getenv("QUIZ_DATA_FILE", "quiz_2016.json")

ENABLE_AI_EXPLANATIONS = os.getenv("ENABLE_AI_EXPLANATIONS", "True").lower() == "true"

# API Settings
GEMINI_MODEL = "gemini-2.0-flash-exp"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent" 