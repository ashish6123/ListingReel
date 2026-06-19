"use client";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

interface ScriptPreviewProps {
  script: string;
}

export function ScriptPreview({ script }: ScriptPreviewProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Generated Script</CardTitle>
        <CardDescription>
          Review the AI-generated script for your listing video.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <p className="whitespace-pre-wrap text-sm leading-relaxed">{script}</p>
      </CardContent>
    </Card>
  );
}
