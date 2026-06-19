import httpx

from app.config import settings

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = (
    "You are a real estate video scriptwriter for short-form social media. "
    "Write a punchy, energetic 45-second script for TikTok/Reels. "
    "Use short sentences. Open with a strong hook. Highlight key features "
    "naturally. Close with a call to action to contact the agent. "
    "Return plain text only. No hashtags. No stage directions."
)


class LLMError(Exception):
    pass


def _build_listing_summary(
    address: str,
    price: float,
    beds: int,
    baths: float,
    sqft: int | None,
    description: str,
) -> str:
    sqft_line = f"\nSquare footage: {sqft}" if sqft else ""
    return (
        f"Address: {address}\n"
        f"Price: ${price:,.0f}\n"
        f"Bedrooms: {beds}\n"
        f"Bathrooms: {baths}"
        f"{sqft_line}\n"
        f"Description: {description}"
    )


async def generate_script(
    address: str,
    price: float,
    beds: int,
    baths: float,
    sqft: int | None,
    description: str,
) -> str:
    listing_summary = _build_listing_summary(
        address, price, beds, baths, sqft, description
    )

    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "content-type": "application/json",
    }
    body = {
        "model": GROQ_MODEL,
        "max_tokens": 1024,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Write a script for this listing:\n\n{listing_summary}",
            },
        ],
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(GROQ_API_URL, headers=headers, json=body)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        raise LLMError(
            f"Groq API error: {exc.response.status_code} {exc.response.text}"
        ) from exc
    except httpx.HTTPError as exc:
        raise LLMError(f"Groq API request failed: {exc}") from exc

    try:
        script = data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMError(f"Unexpected Groq API response shape: {data}") from exc

    if not script:
        raise LLMError("Groq API returned an empty script")

    return script
