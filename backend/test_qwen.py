import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).resolve().parent / ".env")

token = os.getenv("HF_TOKEN")

if not token or token == "hf_your_actual_token_here":
    raise ValueError("HF_TOKEN is missing or invalid in backend/.env")

MODEL = "Qwen/Qwen3.5-27B:novita"

client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=token,
    timeout=120.0
)

def test_qwen():
    print("Connecting to Qwen through Hugging Face...")
    print("Model:", MODEL)

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are a data quality assistant."
            },
            {
                "role": "user",
                "content": "Explain data quality in two simple sentences."
            }
        ],
        max_tokens=200
    )

    answer = response.choices[0].message.content

    if not answer:
        raise RuntimeError("Qwen returned an empty response.")

    print("\nQwen connection successful!")
    print("\nResponse:")
    print(answer)

if __name__ == "__main__":
    try:
        test_qwen()
    except Exception as error:
        print("\nQwen connection failed.")
        print("Error:", type(error).__name__, str(error))
