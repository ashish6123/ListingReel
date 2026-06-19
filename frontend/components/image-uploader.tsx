"use client";

import * as React from "react";
import { ImagePlus, Loader2, X } from "lucide-react";
import { toast } from "sonner";

import { createClient } from "@/lib/supabase/client";
import { cn } from "@/lib/utils";

const MAX_IMAGES = 10;
const MAX_SIZE_BYTES = 10 * 1024 * 1024;
const ACCEPTED_TYPES = ["image/png", "image/jpeg", "image/jpg", "image/webp"];

interface UploadedImage {
  url: string;
  path: string;
  previewUrl: string;
}

interface ImageUploaderProps {
  listingId: string;
  images: UploadedImage[];
  onChange: (images: UploadedImage[]) => void;
  disabled?: boolean;
}

export function ImageUploader({
  listingId,
  images,
  onChange,
  disabled,
}: ImageUploaderProps) {
  const [uploading, setUploading] = React.useState(false);
  const inputRef = React.useRef<HTMLInputElement>(null);
  const supabase = createClient();

  async function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return;

    const remaining = MAX_IMAGES - images.length;
    if (remaining <= 0) {
      toast.error(`You can upload up to ${MAX_IMAGES} images.`);
      return;
    }

    const selected = Array.from(files).slice(0, remaining);

    for (const file of selected) {
      if (!ACCEPTED_TYPES.includes(file.type)) {
        toast.error(`${file.name} is not a supported image type.`);
        continue;
      }
      if (file.size > MAX_SIZE_BYTES) {
        toast.error(`${file.name} is larger than 10MB.`);
        continue;
      }
    }

    const validFiles = selected.filter(
      (f) => ACCEPTED_TYPES.includes(f.type) && f.size <= MAX_SIZE_BYTES
    );
    if (validFiles.length === 0) return;

    setUploading(true);
    try {
      const { data: userData } = await supabase.auth.getUser();
      const userId = userData.user?.id;
      if (!userId) {
        toast.error("You must be logged in to upload images.");
        return;
      }

      const uploaded: UploadedImage[] = [];

      for (const file of validFiles) {
        const ext = file.name.split(".").pop() ?? "jpg";
        const fileName = `${crypto.randomUUID()}.${ext}`;
        const path = `${userId}/${listingId}/${fileName}`;

        const { error } = await supabase.storage
          .from("listing-images")
          .upload(path, file, { contentType: file.type });

        if (error) {
          toast.error(`Failed to upload ${file.name}: ${error.message}`);
          continue;
        }

        const { data: signed } = await supabase.storage
          .from("listing-images")
          .createSignedUrl(path, 60 * 60);

        uploaded.push({
          url: path,
          path,
          previewUrl: signed?.signedUrl ?? "",
        });
      }

      if (uploaded.length > 0) {
        onChange([...images, ...uploaded]);
        toast.success(`Uploaded ${uploaded.length} image(s).`);
      }
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  async function handleRemove(path: string) {
    onChange(images.filter((img) => img.path !== path));
    await supabase.storage.from("listing-images").remove([path]);
  }

  return (
    <div className="space-y-3">
      <div
        className={cn(
          "flex flex-col items-center justify-center gap-2 rounded-md border border-dashed p-6 text-center transition-colors",
          disabled || uploading
            ? "cursor-not-allowed opacity-60"
            : "cursor-pointer hover:border-primary/50 hover:bg-accent/50"
        )}
        onClick={() => {
          if (!disabled && !uploading) inputRef.current?.click();
        }}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          if (!disabled && !uploading) handleFiles(e.dataTransfer.files);
        }}
      >
        {uploading ? (
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        ) : (
          <ImagePlus className="h-6 w-6 text-muted-foreground" />
        )}
        <p className="text-sm text-muted-foreground">
          Drag and drop photos here, or click to browse
        </p>
        <p className="text-xs text-muted-foreground">
          Up to {MAX_IMAGES} images, 10MB each ({images.length}/{MAX_IMAGES} used)
        </p>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED_TYPES.join(",")}
          multiple
          className="hidden"
          disabled={disabled || uploading}
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>

      {images.length > 0 && (
        <div className="grid grid-cols-3 gap-2 sm:grid-cols-5">
          {images.map((img) => (
            <div
              key={img.path}
              className="group relative aspect-square overflow-hidden rounded-md border"
            >
              {img.previewUrl ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={img.previewUrl}
                  alt="Listing photo"
                  className="h-full w-full object-cover"
                />
              ) : (
                <div className="flex h-full w-full items-center justify-center bg-muted text-xs text-muted-foreground">
                  Image
                </div>
              )}
              <button
                type="button"
                onClick={() => handleRemove(img.path)}
                disabled={disabled}
                className="absolute right-1 top-1 rounded-full bg-black/60 p-1 text-white opacity-0 transition-opacity group-hover:opacity-100"
                aria-label="Remove image"
              >
                <X className="h-3 w-3" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export type { UploadedImage };
