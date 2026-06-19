export interface User {
  id: string;
  email: string;
  full_name: string | null;
  is_premium: boolean;
  stripe_customer_id: string | null;
  stripe_subscription_id: string | null;
  videos_used_this_month: number;
  created_at: string;
}

export interface Listing {
  id: string;
  user_id: string;
  address: string;
  price: number;
  beds: number;
  baths: number;
  sqft: number | null;
  description: string;
  image_urls: string[];
  created_at: string;
}

export type VideoStatus = "pending" | "processing" | "completed" | "failed";

export interface Video {
  id: string;
  user_id: string;
  listing_id: string;
  script: string | null;
  voiceover_url: string | null;
  video_url: string | null;
  status: VideoStatus;
  error_message: string | null;
  created_at: string;
}

// ----- API request/response shapes -----

export interface CreateListingRequest {
  address: string;
  price: number;
  beds: number;
  baths: number;
  sqft?: number | null;
  description: string;
  image_urls: string[];
}

export interface GenerateScriptRequest {
  address: string;
  price: number;
  beds: number;
  baths: number;
  sqft?: number | null;
  description: string;
}

export interface GenerateScriptResponse {
  script: string;
}

export interface GenerateVoiceoverRequest {
  listing_id: string;
  script: string;
}

export interface GenerateVoiceoverResponse {
  video_id: string;
  voiceover_url: string;
}

export interface GenerateVideoRequest {
  video_id: string;
}

export interface GenerateVideoResponse {
  video_id: string;
}

export interface VideoStatusResponse {
  status: VideoStatus;
  video_url: string | null;
  error_message?: string | null;
}

export interface CreateOrderResponse {
  order_id: string;
  amount: number;
  currency: string;
  key_id: string;
}

export interface VerifyPaymentRequest {
  razorpay_order_id: string;
  razorpay_payment_id: string;
  razorpay_signature: string;
}

export interface VerifyPaymentResponse {
  is_premium: boolean;
}

export interface VideoCard {
  id: string;
  listing_id: string;
  address: string;
  status: VideoStatus;
  video_url: string | null;
  thumbnail_url: string | null;
  error_message: string | null;
  created_at: string;
}

export interface VideoCardListResponse {
  videos: VideoCard[];
}
