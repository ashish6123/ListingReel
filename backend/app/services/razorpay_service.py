import hashlib
import hmac

import razorpay

from app.config import settings

PRO_PLAN_AMOUNT_PAISE = 99900  # INR 999.00
PRO_PLAN_CURRENCY = "INR"

_client: razorpay.Client | None = None


class RazorpayServiceError(Exception):
    pass


def _get_client() -> razorpay.Client:
    global _client
    if _client is None:
        _client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )
    return _client


def create_order(receipt: str) -> dict:
    try:
        return _get_client().order.create(
            {
                "amount": PRO_PLAN_AMOUNT_PAISE,
                "currency": PRO_PLAN_CURRENCY,
                "receipt": receipt,
                "payment_capture": 1,
            }
        )
    except razorpay.errors.BadRequestError as exc:
        raise RazorpayServiceError(str(exc)) from exc


def verify_payment_signature(order_id: str, payment_id: str, signature: str) -> bool:
    payload = f"{order_id}|{payment_id}".encode("utf-8")
    expected = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode("utf-8"), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
