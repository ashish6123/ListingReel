import httpx

from app.config import settings

ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1/text-to-speech"


class ElevenLabsError(Exception):
    pass


async def generate_voiceover(script: str, voice_id: str | None = None) -> bytes:
    voice = voice_id or settings.ELEVENLABS_VOICE_ID
    url = f"{ELEVENLABS_API_URL}/{voice}"

    headers = {
        "xi-api-key": settings.ELEVENLABS_API_KEY,
        "accept": "audio/mpeg",
        "content-type": "application/json",
    }
    body = {
        "text": script,
        "model_id": "eleven_turbo_v2_5",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, headers=headers, json=body)
            response.raise_for_status()
            return response.content
    except httpx.HTTPStatusError as exc:
        raise ElevenLabsError(
            f"ElevenLabs API error: {exc.response.status_code} {exc.response.text}"
        ) from exc
    except httpx.HTTPError as exc:
        raise ElevenLabsError(f"ElevenLabs API request failed: {exc}") from exc
