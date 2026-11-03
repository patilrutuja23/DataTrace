
import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import errors

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")


def test_gemini():
    if not API_KEY:
        raise ValueError("GEMINI_API_KEY not found in .env")

    client = genai.Client(api_key=API_KEY)

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents="Explain data quality in two sentences."
            )

            if not response.text:
                raise RuntimeError("Gemini returned an empty response")

            print("\nGemini connection successful!")
            print("Model:", MODEL)
            print("\nResponse:")
            print(response.text)
            return

        except errors.ServerError as error:
            if attempt == 2:
                raise

            print(f"Gemini temporarily unavailable. Retry {attempt + 1}/2...")
            time.sleep(5 * (attempt + 1))


if __name__ == "__main__":
    test_gemini()
