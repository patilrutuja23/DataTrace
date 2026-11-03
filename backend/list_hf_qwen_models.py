import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path)

token = os.getenv("HF_TOKEN")

if not token or token == "hf_your_actual_token_here":
    raise ValueError("A real HF_TOKEN is missing from backend/.env")

client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=token,
    timeout=30.0
)

print("Connecting to Hugging Face...")
models = client.models.list()

qwen_models = sorted({
    model.id for model in models.data
    if "qwen" in model.id.lower()
})

if qwen_models:
    print("\nAvailable Qwen models:")
    for model in qwen_models:
        print("-", model)
else:
    print("\nNo Qwen models found in the returned model list.")
