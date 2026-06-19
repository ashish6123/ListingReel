from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ListingCreate(BaseModel):
    address: str = Field(min_length=1, max_length=500)
    price: float = Field(gt=0)
    beds: int = Field(ge=0, le=50)
    baths: float = Field(ge=0, le=50)
    sqft: Optional[int] = Field(default=None, ge=0)
    description: str = Field(min_length=1, max_length=5000)
    image_urls: list[str] = Field(default_factory=list, max_length=10)


class ListingResponse(BaseModel):
    id: str
    user_id: str
    address: str
    price: float
    beds: int
    baths: float
    sqft: Optional[int]
    description: str
    image_urls: list[str]
    created_at: datetime


class ListingListResponse(BaseModel):
    listings: list[ListingResponse]


class GenerateScriptRequest(BaseModel):
    address: str = Field(min_length=1, max_length=500)
    price: float = Field(gt=0)
    beds: int = Field(ge=0, le=50)
    baths: float = Field(ge=0, le=50)
    sqft: Optional[int] = Field(default=None, ge=0)
    description: str = Field(min_length=1, max_length=5000)


class GenerateScriptResponse(BaseModel):
    script: str


class GenerateVoiceoverRequest(BaseModel):
    listing_id: str
    script: str = Field(min_length=1, max_length=10000)


class GenerateVoiceoverResponse(BaseModel):
    video_id: str
    voiceover_url: str


class GenerateVideoRequest(BaseModel):
    video_id: str


class GenerateVideoResponse(BaseModel):
    video_id: str


class VideoStatusResponse(BaseModel):
    status: str
    video_url: Optional[str] = None
    error_message: Optional[str] = None


class CreateOrderResponse(BaseModel):
    order_id: str
    amount: int
    currency: str
    key_id: str


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str = Field(min_length=1)
    razorpay_payment_id: str = Field(min_length=1)
    razorpay_signature: str = Field(min_length=1)


class VerifyPaymentResponse(BaseModel):
    is_premium: bool


class VideoCardResponse(BaseModel):
    id: str
    listing_id: str
    address: str
    status: str
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime


class VideoCardListResponse(BaseModel):
    videos: list[VideoCardResponse]
