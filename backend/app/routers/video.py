import os
import shutil
import tempfile
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from supabase import Client

from app.dependencies import get_current_user, get_db
from app.limiter import limiter
from app.models.schemas import (
    GenerateVideoRequest,
    GenerateVideoResponse,
    VideoCardListResponse,
    VideoCardResponse,
    VideoStatusResponse,
)
from app.services.ffmpeg import FFmpegError, build_video
from app.services.storage import StorageError, create_signed_url, download_file, upload_file

router = APIRouter(prefix="/api", tags=["video"])

FREE_TIER_VIDEO_LIMIT = 3
STUCK_PROCESSING_THRESHOLD_MINUTES = 10


def reap_stuck_videos(db: Client) -> int:
    """Marks videos stuck in 'processing' as failed.

    A background task can die without ever reaching its except block if the
    Render container itself is restarted/OOM-killed mid-encode - the DB row
    then sits in 'processing' forever with no error written. This sweep
    catches those orphaned rows so users get a Retry button instead of an
    infinite spinner.
    """
    cutoff = (
        datetime.now(timezone.utc) - timedelta(minutes=STUCK_PROCESSING_THRESHOLD_MINUTES)
    ).isoformat()
    result = (
        db.table("videos")
        .update(
            {
                "status": "failed",
                "error_message": "Video generation was interrupted by a server restart. Please retry.",
            }
        )
        .eq("status", "processing")
        .lt("updated_at", cutoff)
        .execute()
    )
    return len(result.data)


def _maybe_reset_usage(user_row: dict) -> dict:
    """Returns update fields if the stored usage month is stale, else empty dict."""
    reset_at_raw = user_row.get("usage_reset_at")
    now = datetime.now(timezone.utc)

    if reset_at_raw:
        reset_at = datetime.fromisoformat(reset_at_raw.replace("Z", "+00:00"))
        if reset_at.year == now.year and reset_at.month == now.month:
            return {}

    return {
        "videos_used_this_month": 0,
        "usage_reset_at": now.isoformat(),
    }


@router.post(
    "/generate-video",
    response_model=GenerateVideoResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit("10/minute")
async def generate_video_route(
    request: Request,
    payload: GenerateVideoRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user),
    db: Client = Depends(get_db),
) -> GenerateVideoResponse:
    user_result = (
        db.table("users")
        .select("is_premium, videos_used_this_month, usage_reset_at")
        .eq("id", user_id)
        .single()
        .execute()
    )
    user_row = user_result.data
    if not user_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    reset_fields = _maybe_reset_usage(user_row)
    if reset_fields:
        db.table("users").update(reset_fields).eq("id", user_id).execute()
        user_row = {**user_row, **reset_fields}

    if not user_row["is_premium"] and user_row["videos_used_this_month"] >= FREE_TIER_VIDEO_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "upgrade_required"},
        )

    video_result = (
        db.table("videos")
        .select("id, script, voiceover_url, listing_id")
        .eq("id", payload.video_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not video_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Video not found"
        )

    video_row = video_result.data[0]
    if not video_row["voiceover_url"] or not video_row["script"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Video is missing a script or voiceover. Generate those first.",
        )

    db.table("videos").update({"status": "pending", "error_message": None}).eq(
        "id", payload.video_id
    ).execute()

    if not user_row["is_premium"]:
        db.table("users").update(
            {"videos_used_this_month": user_row["videos_used_this_month"] + 1}
        ).eq("id", user_id).execute()

    background_tasks.add_task(process_video, payload.video_id, user_id)

    return GenerateVideoResponse(video_id=payload.video_id)


@router.get("/videos", response_model=VideoCardListResponse)
async def list_videos_route(
    user_id: str = Depends(get_current_user),
    db: Client = Depends(get_db),
) -> VideoCardListResponse:
    videos_result = (
        db.table("videos")
        .select("id, listing_id, status, video_url, error_message, created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    video_rows = videos_result.data
    if not video_rows:
        return VideoCardListResponse(videos=[])

    listing_ids = list({row["listing_id"] for row in video_rows})
    listings_result = (
        db.table("listings")
        .select("id, address, image_urls")
        .in_("id", listing_ids)
        .execute()
    )
    listings_by_id = {row["id"]: row for row in listings_result.data}

    cards: list[VideoCardResponse] = []
    for row in video_rows:
        listing = listings_by_id.get(row["listing_id"], {})
        image_urls = listing.get("image_urls") or []

        thumbnail_url = None
        if image_urls:
            try:
                thumbnail_url = create_signed_url(db, "listing-images", image_urls[0])
            except StorageError:
                thumbnail_url = None

        video_url = None
        if row["status"] == "completed" and row["video_url"]:
            try:
                video_url = create_signed_url(db, "videos", row["video_url"])
            except StorageError:
                video_url = None

        cards.append(
            VideoCardResponse(
                id=row["id"],
                listing_id=row["listing_id"],
                address=listing.get("address", "Unknown listing"),
                status=row["status"],
                video_url=video_url,
                thumbnail_url=thumbnail_url,
                error_message=row["error_message"],
                created_at=row["created_at"],
            )
        )

    return VideoCardListResponse(videos=cards)


@router.get("/video-status/{video_id}", response_model=VideoStatusResponse)
async def video_status_route(
    video_id: str,
    user_id: str = Depends(get_current_user),
    db: Client = Depends(get_db),
) -> VideoStatusResponse:
    result = (
        db.table("videos")
        .select("status, video_url, error_message")
        .eq("id", video_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Video not found"
        )

    row = result.data[0]
    video_url = None
    if row["status"] == "completed" and row["video_url"]:
        try:
            video_url = create_signed_url(db, "videos", row["video_url"])
        except StorageError:
            video_url = None

    return VideoStatusResponse(
        status=row["status"],
        video_url=video_url,
        error_message=row["error_message"],
    )


def process_video(video_id: str, user_id: str) -> None:
    # NOTE: deliberately a sync `def`, not `async def`. Everything below is
    # blocking (ffmpeg subprocess, file I/O, sync supabase calls). As an
    # `async def` background task it ran *on the event loop* and froze the
    # entire server for the whole ~minute-long encode - uvicorn couldn't
    # answer Render's health checks, so Render restarted the container
    # mid-encode every time. As a plain `def`, FastAPI/Starlette runs it in
    # a worker thread and the event loop stays responsive.
    db = get_db()
    work_dir = tempfile.mkdtemp(prefix=f"listingreel_{video_id}_")

    try:
        db.table("videos").update({"status": "processing"}).eq("id", video_id).execute()

        video_result = (
            db.table("videos")
            .select("script, voiceover_url, listing_id")
            .eq("id", video_id)
            .single()
            .execute()
        )
        video_row = video_result.data
        script = video_row["script"]
        voiceover_path = video_row["voiceover_url"]
        listing_id = video_row["listing_id"]

        listing_result = (
            db.table("listings")
            .select("image_urls")
            .eq("id", listing_id)
            .single()
            .execute()
        )
        image_urls: list[str] = listing_result.data["image_urls"]
        if not image_urls:
            raise FFmpegError("Listing has no images")

        audio_path = os.path.join(work_dir, "voiceover.mp3")
        audio_bytes = download_file(db, "voiceovers", voiceover_path)
        with open(audio_path, "wb") as f:
            f.write(audio_bytes)

        local_image_paths: list[str] = []
        for i, image_path in enumerate(image_urls):
            ext = os.path.splitext(image_path)[1] or ".jpg"
            local_path = os.path.join(work_dir, f"image_{i}{ext}")
            image_bytes = download_file(db, "listing-images", image_path)
            with open(local_path, "wb") as f:
                f.write(image_bytes)
            local_image_paths.append(local_path)

        output_path = os.path.join(work_dir, "final.mp4")
        build_video(local_image_paths, audio_path, output_path, script)

        with open(output_path, "rb") as f:
            video_bytes = f.read()

        storage_path = f"{user_id}/{video_id}/final.mp4"
        upload_file(db, "videos", storage_path, video_bytes, "video/mp4")

        db.table("videos").update(
            {"status": "completed", "video_url": storage_path, "error_message": None}
        ).eq("id", video_id).execute()
    except Exception as exc:  # noqa: BLE001
        db.table("videos").update(
            {"status": "failed", "error_message": str(exc)}
        ).eq("id", video_id).execute()
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
