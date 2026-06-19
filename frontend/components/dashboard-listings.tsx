"use client";

import * as React from "react";

import { ListingForm } from "@/components/listing-form";
import { ScriptPreview } from "@/components/script-preview";
import { VideoGenerationProgress } from "@/components/video-generation-progress";
import { VideoList, type VideoListRef } from "@/components/video-list";
import type { Listing } from "@/types";

export function DashboardListings() {
  const [activeListing, setActiveListing] = React.useState<Listing | null>(null);
  const [generatedScript, setGeneratedScript] = React.useState<string | null>(
    null
  );
  const videoListRef = React.useRef<VideoListRef>(null);

  return (
    <div className="space-y-8">
      <ListingForm
        onCreated={(listing) => {
          setGeneratedScript(null);
          setActiveListing(listing);
        }}
      />

      {activeListing && (
        <VideoGenerationProgress
          key={activeListing.id}
          listing={activeListing}
          onScriptGenerated={setGeneratedScript}
          onVideoCompleted={() => videoListRef.current?.refresh()}
        />
      )}

      {generatedScript && <ScriptPreview script={generatedScript} />}

      <VideoList ref={videoListRef} />
    </div>
  );
}
