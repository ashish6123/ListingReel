"use client";

import * as React from "react";
import {
  CheckCircle2,
  Circle,
  Download,
  Loader2,
  RefreshCw,
  XCircle,
} from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { api, ApiError } from "@/lib/api";
import type {
  GenerateScriptRequest,
  GenerateScriptResponse,
  GenerateVideoRequest,
  GenerateVideoResponse,
  GenerateVoiceoverRequest,
  GenerateVoiceoverResponse,
  Listing,
  VideoStatusResponse,
} from "@/types";

type StepKey = "script" | "voiceover" | "video" | "done";

const STEPS: { key: StepKey; label: string }[] = [
  { key: "script", label: "Generating script" },
  { key: "voiceover", label: "Creating voiceover" },
  { key: "video", label: "Assembling video" },
  { key: "done", label: "Ready to download" },
];

const STEP_ORDER: StepKey[] = ["script", "voiceover", "video", "done"];

interface VideoGenerationProgressProps {
  listing: Listing;
  onScriptGenerated?: (script: string) => void;
  onVideoCompleted?: () => void;
}

export function VideoGenerationProgress({
  listing,
  onScriptGenerated,
  onVideoCompleted,
}: VideoGenerationProgressProps) {
  const [currentStep, setCurrentStep] = React.useState<StepKey>("script");
  const [failed, setFailed] = React.useState<string | null>(null);
  const [videoUrl, setVideoUrl] = React.useState<string | null>(null);
  const [attempt, setAttempt] = React.useState(0);

  React.useEffect(() => {
    let cancelled = false;
    let pollTimer: ReturnType<typeof setTimeout> | null = null;

    async function run() {
      try {
        setFailed(null);
        setVideoUrl(null);
        setCurrentStep("script");

        const { script: generatedScript } = await api.post<GenerateScriptResponse>(
          "/api/generate-script",
          {
            address: listing.address,
            price: listing.price,
            beds: listing.beds,
            baths: listing.baths,
            sqft: listing.sqft,
            description: listing.description,
          } satisfies GenerateScriptRequest
        );
        if (cancelled) return;
        onScriptGenerated?.(generatedScript);
        toast.success("Script generated.");
        setCurrentStep("voiceover");

        const voiceoverRes = await api.post<GenerateVoiceoverResponse>(
          "/api/generate-voiceover",
          {
            listing_id: listing.id,
            script: generatedScript,
          } satisfies GenerateVoiceoverRequest
        );
        if (cancelled) return;
        toast.success("Voiceover generated.");
        setCurrentStep("video");

        try {
          await api.post<GenerateVideoResponse>("/api/generate-video", {
            video_id: voiceoverRes.video_id,
          } satisfies GenerateVideoRequest);
        } catch (err) {
          // A real HTTP error response (4xx/5xx) means the server rejected
          // the request - that's a genuine failure. But a network-level
          // error (dropped connection, e.g. a backend restart mid-request)
          // means we don't actually know whether the job started server
          // side. Fall back to polling instead of failing outright, since
          // the background task may already be running.
          if (err instanceof ApiError) throw err;
        }
        if (cancelled) return;
        toast.success("Assembling your video...");

        const poll = async () => {
          if (cancelled) return;
          try {
            const statusRes = await api.get<VideoStatusResponse>(
              `/api/video-status/${voiceoverRes.video_id}`
            );
            if (cancelled) return;

            if (statusRes.status === "completed") {
              setVideoUrl(statusRes.video_url);
              setCurrentStep("done");
              toast.success("Your video is ready!");
              onVideoCompleted?.();
              return;
            }
            if (statusRes.status === "failed") {
              const message =
                statusRes.error_message ?? "Video generation failed.";
              setFailed(message);
              toast.error(message);
              return;
            }
            pollTimer = setTimeout(poll, 3000);
          } catch {
            pollTimer = setTimeout(poll, 3000);
          }
        };

        pollTimer = setTimeout(poll, 3000);
      } catch (err) {
        if (cancelled) return;
        if (
          err instanceof ApiError &&
          err.status === 403 &&
          typeof err.body === "object" &&
          err.body &&
          "detail" in err.body &&
          typeof (err.body as { detail: unknown }).detail === "object" &&
          (err.body as { detail: { code?: string } }).detail?.code ===
            "upgrade_required"
        ) {
          setFailed(
            "You've reached your free plan limit of 3 videos this month. Upgrade to Pro for unlimited videos."
          );
          return;
        }

        const message =
          err instanceof ApiError &&
          typeof err.body === "object" &&
          err.body &&
          "detail" in err.body
            ? String((err.body as { detail: unknown }).detail)
            : "Something went wrong while generating your video.";
        setFailed(message);
        toast.error(message);
      }
    }

    run();

    return () => {
      cancelled = true;
      if (pollTimer) clearTimeout(pollTimer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [listing.id, attempt]);

  const currentIndex = STEP_ORDER.indexOf(currentStep);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Generating Your Video</CardTitle>
        <CardDescription>{listing.address}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <ol className="space-y-3">
          {STEPS.map((step, idx) => {
            const isDone = !failed && (idx < currentIndex || currentStep === "done" && idx <= currentIndex);
            const isActive = !failed && idx === currentIndex && currentStep !== "done";
            const isFailedHere = !!failed && idx === currentIndex;

            return (
              <li key={step.key} className="flex items-center gap-3 text-sm">
                {isFailedHere ? (
                  <XCircle className="h-5 w-5 text-destructive" />
                ) : isDone ? (
                  <CheckCircle2 className="h-5 w-5 text-green-600" />
                ) : isActive ? (
                  <Loader2 className="h-5 w-5 animate-spin text-primary" />
                ) : (
                  <Circle className="h-5 w-5 text-muted-foreground" />
                )}
                <span
                  className={
                    isDone
                      ? "text-foreground"
                      : isActive
                        ? "font-medium text-foreground"
                        : "text-muted-foreground"
                  }
                >
                  {step.label}
                </span>
              </li>
            );
          })}
        </ol>

        {failed && (
          <div className="space-y-3">
            <p className="rounded-md border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
              {failed}
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setAttempt((a) => a + 1)}
            >
              <RefreshCw className="mr-2 h-4 w-4" />
              Retry
            </Button>
          </div>
        )}

        {videoUrl && (
          <Button asChild>
            <a href={videoUrl} download={`listingreel-${listing.id}.mp4`}>
              <Download className="mr-2 h-4 w-4" />
              Download Video
            </a>
          </Button>
        )}
      </CardContent>

    </Card>
  );
}
