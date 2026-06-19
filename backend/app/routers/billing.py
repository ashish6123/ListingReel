from fastapi import APIRouter, Depends, HTTPException, status
from postgrest.exceptions import APIError
from supabase import Client

from app.config import settings
from app.dependencies import get_current_user, get_db
from app.models.schemas import (
    CreateOrderResponse,
    VerifyPaymentRequest,
    VerifyPaymentResponse,
)
from app.services.razorpay_service import (
    RazorpayServiceError,
    create_order,
    verify_payment_signature,
)

router = APIRouter(prefix="/api/billing", tags=["billing"])


@router.post("/create-order", response_model=CreateOrderResponse)
async def create_order_route(
    user_id: str = Depends(get_current_user),
    db: Client = Depends(get_db),
) -> CreateOrderResponse:
    user_result = (
        db.table("users")
        .select("is_premium")
        .eq("id", user_id)
        .single()
        .execute()
    )
    user_row = user_result.data
    if not user_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    if user_row["is_premium"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already on the Pro plan",
        )

    try:
        order = create_order(receipt=f"up_{user_id}"[:40])
    except RazorpayServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to create order: {exc}",
        ) from exc

    return CreateOrderResponse(
        order_id=order["id"],
        amount=order["amount"],
        currency=order["currency"],
        key_id=settings.RAZORPAY_KEY_ID,
    )


@router.post("/verify-payment", response_model=VerifyPaymentResponse)
async def verify_payment_route(
    payload: VerifyPaymentRequest,
    user_id: str = Depends(get_current_user),
    db: Client = Depends(get_db),
) -> VerifyPaymentResponse:
    if not verify_payment_signature(
        payload.razorpay_order_id,
        payload.razorpay_payment_id,
        payload.razorpay_signature,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment signature verification failed",
        )

    try:
        db.table("users").update(
            {
                "is_premium": True,
                "razorpay_payment_id": payload.razorpay_payment_id,
            }
        ).eq("id", user_id).execute()
    except APIError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update account: {exc.message}",
        ) from exc

    return VerifyPaymentResponse(is_premium=True)
