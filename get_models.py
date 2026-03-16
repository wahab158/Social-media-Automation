import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

try:
    models = client.models.list()
    # Write to a file instead of stdout to avoid buffering issues
    with open("available_models.json", "w") as f:
        json.dump([m.id for m in models.data], f)
    print("SUCCESS")
except Exception as e:
    print(f"FAILED: {e}")
