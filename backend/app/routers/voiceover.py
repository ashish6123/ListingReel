from fastapi import APIRouter, Depends, HTTPException, Request, status
from postgrest.exceptions import APIError
from supabase import Client

from app.dependencies import get_current_user, get_db
from app.limiter import limiter
from app.models.schemas import GenerateVoiceoverRequest, GenerateVoiceoverResponse
from app.services.elevenlabs import ElevenLabsError, generate_voiceover
from app.services.storage import StorageError, create_signed_url, upload_file

router = APIRouter(prefix="/api", tags=["voiceover"])


@router.post("/generate-voiceover", response_model=GenerateVoiceoverResponse)
@limiter.limit("20/minute")
async def generate_voiceover_route(
    request: Request,
    payload: GenerateVoiceoverRequest,
    user_id: str = Depends(get_current_user),
    db: Client = Depends(get_db),
) -> GenerateVoiceoverResponse:
    listing_result = (
        db.table("listings")
        .select("id")
        .eq("id", payload.listing_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not listing_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found"
        )

    try:
        video_result = (
            db.table("videos")
            .insert(
                {
                    "user_id": user_id,
                    "listing_id": payload.listing_id,
                    "script": payload.script,
                    "status": "pending",
                }
            )
            .execute()
        )
    except APIError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create video record: {exc.message}",
        ) from exc

    if not video_result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create video record",
        )

    video_id = video_result.data[0]["id"]

    try:
        audio_bytes = await generate_voiceover(payload.script)
    except ElevenLabsError as exc:
        db.table("videos").update(
            {"status": "failed", "error_message": str(exc)}
        ).eq("id", video_id).execute()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to generate voiceover: {exc}",
        ) from exc

    voiceover_path = f"{user_id}/{video_id}/voiceover.mp3"

    try:
        upload_file(db, "voiceovers", voiceover_path, audio_bytes, "audio/mpeg")
        signed_url = create_signed_url(db, "voiceovers", voiceover_path)
    except StorageError as exc:
        db.table("videos").update(
            {"status": "failed", "error_message": str(exc)}
        ).eq("id", video_id).execute()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store voiceover: {exc}",
        ) from exc

    db.table("videos").update({"voiceover_url": voiceover_path}).eq(
        "id", video_id
    ).execute()

    return GenerateVoiceoverResponse(video_id=video_id, voiceover_url=signed_url)
