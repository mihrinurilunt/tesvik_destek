import os
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")


async def create_embedding(text: str) -> list[float]:
    response = await client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
    )

    return response.data[0].embedding


async def generate_llm_answer(prompt: str) -> str:
    response = await client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "Sen Türkiye'deki teşvik ve destek programları hakkında "
                    "belgeye dayalı cevap veren bir asistansın. "
                    "Sadece verilen kaynaklara dayan. Emin değilsen belirt."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )

    return response.choices[0].message.content or ""