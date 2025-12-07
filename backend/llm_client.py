from typing import List, Optional
from groq import Groq
from .config import GROQ_API_KEY

if not GROQ_API_KEY or GROQ_API_KEY == "YOUR_GROQ_API_KEY_HERE":
    raise RuntimeError("GROQ_API_KEY is missing in backend/config.py")

client = Groq(api_key=GROQ_API_KEY)


def chat_with_llm(
    prompt: str,
    system_message: Optional[str] = None,
    history: Optional[List[str]] = None,
) -> str:
    messages = []

    if system_message:
        messages.append({"role": "system", "content": system_message})

    if history:
        for msg in history:
            if msg.startswith("User:"):
                messages.append(
                    {"role": "user", "content": msg.replace("User:", "").strip()}
                )
            elif msg.startswith("Assistant:"):
                messages.append(
                    {
                        "role": "assistant",
                        "content": msg.replace("Assistant:", "").strip(),
                    }
                )

    messages.append({"role": "user", "content": prompt})

    # response = client.chat.completions.create(
    #     model="llama-3.1-8b-instant",
    #     messages=messages,
    #     temperature=0.4,
    #     max_tokens=2000,
    # )
    #meta-llama/llama-4-scout-17b-16e-instruct

    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=messages,
        temperature=0.4,
        max_tokens=2000,
    )
    return response.choices[0].message.content.strip()













