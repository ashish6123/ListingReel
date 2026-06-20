"use client";

import * as React from "react";
import { Download, ImageOff, Loader2, Play, RefreshCw, X } from "lucide-react";
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
  GenerateVideoRequest,
  GenerateVideoResponse,
  VideoCard,
  VideoCardListResponse,
} from "@/types";

function errorMessage(err: unknown, fallback: string): string {
  if (!(err instanceof ApiError) || typeof err.body !== "object" || !err.body) {
    return fallback;
  }
  if (!("detail" in err.body)) {
    return fallback;
  }
  const detail = (err.body as { detail: unknown }).detail;
  if (typeof detail === "string") {
    return detail;
  }
  if (
    typeof detail === "object" &&
    detail &&
    "code" in detail &&
    (detail as { code: unknown }).code === "upgrade_required"
  ) {
    return "You've reached your free plan limit of 3 videos this month. Upgrade to Pro for unlimited videos.";
  }
  return fallback;
}

const ACTIVE_STATUSES = new Set(["pending", "processing"]);

const STATUS_LABELS: Record<string, string> = {
  pending: "Pending",
  processing: "Processing",
  completed: "Ready",
  failed: "Failed",
};

const STATUS_BADGE_CLASSES: Record<string, string> = {
  pending: "bg-amber-100 text-amber-800",
  processing: "bg-blue-100 text-blue-800",
  completed: "bg-green-100 text-green-800",
  failed: "bg-destructive/10 text-destructive",
};

export interface VideoListRef {
  refresh: () => void;
}

function VideoPlayerModal({
  video,
  onClose,
}: {
  video: VideoCard;
  onClose: () => void;
}) {
  React.useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-sm"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={onClose}
          className="absolute -right-3 -top-3 z-10 flex h-7 w-7 items-center justify-center rounded-full bg-white text-black shadow-md hover:bg-gray-100"
        >
          <X className="h-4 w-4" />
        </button>
        <video
          src={video.video_url!}
          controls
          autoPlay
          className="w-full rounded-lg shadow-2xl"
          style={{ aspectRatio: "9/16" }}
        />
        <div className="mt-3 flex items-center justify-between">
          <p className="truncate text-sm font-medium text-white">{video.address}</p>
          <a
            href={video.video_url!}
            download={`listingreel-${video.id}.mp4`}
            className="ml-3 flex shrink-0 items-center gap-1.5 rounded-md bg-white px-3 py-1.5 text-xs font-medium text-black hover:bg-gray-100"
          >
            <Download className="h-3.5 w-3.5" />
            Download
          </a>
        </div>
      </div>
    </div>
  );
}

export const VideoList = React.forwardRef<VideoListRef>(function VideoList(
  _props,
  ref
) {
  const [videos, setVideos] = React.useState<VideoCard[] | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [retrying, setRetrying] = React.useState<string | null>(null);
  const [playing, setPlaying] = React.useState<VideoCard | null>(null);

  const refresh = React.useCallback(async () => {
    try {
      const data = await api.get<VideoCardListResponse>("/api/videos");
      setVideos(data.videos);
    } catch {
      setVideos((prev) => prev ?? []);
    } finally {
      setLoading(false);
    }
  }, []);

  React.useImperativeHandle(ref, () => ({ refresh }), [refresh]);

  React.useEffect(() => {
    refresh();
  }, [refresh]);

  React.useEffect(() => {
    const hasActive = videos?.some((v) => ACTIVE_STATUSES.has(v.status));
    if (!hasActive) return;
    const timer = setInterval(refresh, 3000);
    return () => clearInterval(timer);
  }, [videos, refresh]);

  const handleRetry = async (video: VideoCard) => {
    setRetrying(video.id);
    try {
      await api.post<GenerateVideoResponse>("/api/generate-video", {
        video_id: video.id,
      } satisfies GenerateVideoRequest);
      toast.success("Retrying video generation...");
      await refresh();
    } catch (err) {
      toast.error(errorMessage(err, "Failed to retry video generation."));
    } finally {
      setRetrying(null);
    }
  };

  return (
    <>
      {playing && (
        <VideoPlayerModal video={playing} onClose={() => setPlaying(null)} />
      )}

      <Card>
        <CardHeader>
          <CardTitle>My Videos</CardTitle>
          <CardDescription>
            Your generated videos will appear here.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex h-32 items-center justify-center text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin" />
            </div>
          ) : !videos || videos.length === 0 ? (
            <div className="flex h-32 items-center justify-center rounded-md border border-dashed text-sm text-muted-foreground">
              No videos yet. Create a listing to get started.
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {videos.map((video) => (
                <div
                  key={video.id}
                  className="overflow-hidden rounded-md border text-sm"
                >
                  <div
                    className={`relative flex aspect-video items-center justify-center bg-muted ${
                      video.status === "completed" && video.video_url
                        ? "cursor-pointer group"
                        : ""
                    }`}
                    onClick={() => {
                      if (video.status === "completed" && video.video_url) {
                        setPlaying(video);
                      }
                    }}
                  >
                    {video.thumbnail_url ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={video.thumbnail_url}
                        alt={video.address}
                        className="h-full w-full object-cover"
                      />
                    ) : (
                      <ImageOff className="h-8 w-8 text-muted-foreground" />
                    )}
                    {video.status === "completed" && video.video_url && (
                      <div className="absolute inset-0 flex items-center justify-center bg-black/30 opacity-0 transition-opacity group-hover:opacity-100">
                        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-white/90 shadow-lg">
                          <Play className="h-5 w-5 translate-x-0.5 text-black" />
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="space-y-2 p-4">
                    <div className="flex items-start justify-between gap-2">
                      <p className="font-medium leading-tight">{video.address}</p>
                      <span
                        className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${
                          STATUS_BADGE_CLASSES[video.status] ??
                          "bg-muted text-muted-foreground"
                        }`}
                      >
                        {(video.status === "pending" ||
                          video.status === "processing") && (
                          <Loader2 className="mr-1 inline h-3 w-3 animate-spin" />
                        )}
                        {STATUS_LABELS[video.status] ?? video.status}
                      </span>
                    </div>

                    {video.status === "failed" && video.error_message && (
                      <p className="line-clamp-2 text-xs text-destructive">
                        {video.error_message}
                      </p>
                    )}

                    {video.status === "completed" && video.video_url && (
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          className="flex-1"
                          onClick={() => setPlaying(video)}
                        >
                          <Play className="mr-2 h-4 w-4" />
                          Watch
                        </Button>
                        <Button asChild size="sm" variant="outline">
                          <a
                            href={video.video_url}
                            download={`listingreel-${video.id}.mp4`}
                          >
                            <Download className="h-4 w-4" />
                          </a>
                        </Button>
                      </div>
                    )}

                    {video.status === "failed" && (
                      <Button
                        size="sm"
                        variant="outline"
                        className="w-full"
                        disabled={retrying === video.id}
                        onClick={() => handleRetry(video)}
                      >
                        {retrying === video.id ? (
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        ) : (
                          <RefreshCw className="mr-2 h-4 w-4" />
                        )}
                        Retry
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </>
  );
});
