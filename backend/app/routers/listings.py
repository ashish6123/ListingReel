from fastapi import APIRouter, Depends, HTTPException, status
from postgrest.exceptions import APIError
from supabase import Client

from app.dependencies import get_current_user, get_db
from app.models.schemas import ListingCreate, ListingListResponse, ListingResponse

router = APIRouter(prefix="/api/listings", tags=["listings"])


def _assert_owns_image_paths(user_id: str, image_urls: list[str]) -> None:
    """Storage paths are scoped per-user as `{user_id}/...`. Reject any path
    that doesn't belong to the requesting user - otherwise a client could
    submit another user's storage path and have it signed/read server-side
    via the service-role client, which bypasses Storage RLS."""
    prefix = f"{user_id}/"
    for path in image_urls:
        if not path.startswith(prefix):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="One or more image paths do not belong to this account.",
            )


@router.post("", response_model=ListingResponse, status_code=status.HTTP_201_CREATED)
async def create_listing(
    payload: ListingCreate,
    user_id: str = Depends(get_current_user),
    db: Client = Depends(get_db),
) -> ListingResponse:
    _assert_owns_image_paths(user_id, payload.image_urls)

    try:
        result = (
            db.table("listings")
            .insert(
                {
                    "user_id": user_id,
                    "address": payload.address,
                    "price": payload.price,
                    "beds": payload.beds,
                    "baths": payload.baths,
                    "sqft": payload.sqft,
                    "description": payload.description,
                    "image_urls": payload.image_urls,
                }
            )
            .execute()
        )
    except APIError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create listing: {exc.message}",
        ) from exc

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create listing",
        )

    return ListingResponse(**result.data[0])


@router.get("", response_model=ListingListResponse)
async def list_listings(
    user_id: str = Depends(get_current_user),
    db: Client = Depends(get_db),
) -> ListingListResponse:
    try:
        result = (
            db.table("listings")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
    except APIError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch listings: {exc.message}",
        ) from exc

    return ListingListResponse(listings=[ListingResponse(**row) for row in result.data])
