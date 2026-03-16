import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

try:
    models = client.models.list()
    for model in models.data:
        print(f"Model ID: {model.id}")
except Exception as e:
    print(f"Error listing models: {e}")
