"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { api, ApiError } from "@/lib/api";
import type {
  CreateOrderResponse,
  VerifyPaymentRequest,
  VerifyPaymentResponse,
} from "@/types";

declare global {
  interface Window {
    Razorpay: new (options: Record<string, unknown>) => {
      open: () => void;
    };
  }
}

const RAZORPAY_SCRIPT_SRC = "https://checkout.razorpay.com/v1/checkout.js";

function errorMessage(err: unknown, fallback: string): string {
  if (
    err instanceof ApiError &&
    typeof err.body === "object" &&
    err.body &&
    "detail" in err.body
  ) {
    return String((err.body as { detail: unknown }).detail);
  }
  return fallback;
}

function loadRazorpayScript(): Promise<void> {
  return new Promise((resolve, reject) => {
    if (window.Razorpay) {
      resolve();
      return;
    }
    const script = document.createElement("script");
    script.src = RAZORPAY_SCRIPT_SRC;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Failed to load Razorpay checkout"));
    document.body.appendChild(script);
  });
}

export function BillingActions({
  isPremium,
  userEmail,
}: {
  isPremium: boolean;
  userEmail: string;
}) {
  const [loading, setLoading] = React.useState(false);
  const router = useRouter();

  const handleUpgrade = async () => {
    setLoading(true);
    try {
      await loadRazorpayScript();

      const order = await api.post<CreateOrderResponse>(
        "/api/billing/create-order"
      );

      const razorpay = new window.Razorpay({
        key: order.key_id,
        amount: order.amount,
        currency: order.currency,
        order_id: order.order_id,
        name: "ListingReel",
        description: "ListingReel Pro - Monthly Subscription",
        prefill: { email: userEmail },
        theme: { color: "#0f172a" },
        handler: async (response: {
          razorpay_order_id: string;
          razorpay_payment_id: string;
          razorpay_signature: string;
        }) => {
          try {
            await api.post<VerifyPaymentResponse>(
              "/api/billing/verify-payment",
              {
                razorpay_order_id: response.razorpay_order_id,
                razorpay_payment_id: response.razorpay_payment_id,
                razorpay_signature: response.razorpay_signature,
              } satisfies VerifyPaymentRequest
            );
            toast.success("You're now on the Pro plan!");
            router.refresh();
          } catch (err) {
            toast.error(errorMessage(err, "Payment verification failed."));
          } finally {
            setLoading(false);
          }
        },
        modal: {
          ondismiss: () => setLoading(false),
        },
      });

      razorpay.open();
    } catch (err) {
      toast.error(errorMessage(err, "Failed to start checkout."));
      setLoading(false);
    }
  };

  if (isPremium) {
    return (
      <span className="rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
        Pro plan active
      </span>
    );
  }

  return (
    <Button size="sm" onClick={handleUpgrade} disabled={loading}>
      {loading ? "Loading..." : "Upgrade to Pro - ₹999/mo"}
    </Button>
  );
}
