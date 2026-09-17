from dotenv import load_dotenv
import os
from openai import OpenAI

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

api_key = os.getenv("GROQ_API_KEY")
print("Loaded key starts with:", api_key[:8] if api_key else "NONE FOUND")

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=api_key,
)

for m in client.models.list().data:
    print(m.id)