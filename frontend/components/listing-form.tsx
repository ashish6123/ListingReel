"use client";

import * as React from "react";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { ImageUploader, type UploadedImage } from "@/components/image-uploader";
import { api, ApiError } from "@/lib/api";
import type { CreateListingRequest, Listing } from "@/types";

interface ListingFormProps {
  onCreated?: (listing: Listing) => void;
}

export function ListingForm({ onCreated }: ListingFormProps) {
  const [draftId] = React.useState(() => crypto.randomUUID());
  const [address, setAddress] = React.useState("");
  const [price, setPrice] = React.useState("");
  const [beds, setBeds] = React.useState("");
  const [baths, setBaths] = React.useState("");
  const [sqft, setSqft] = React.useState("");
  const [description, setDescription] = React.useState("");
  const [images, setImages] = React.useState<UploadedImage[]>([]);
  const [submitting, setSubmitting] = React.useState(false);

  function resetForm() {
    setAddress("");
    setPrice("");
    setBeds("");
    setBaths("");
    setSqft("");
    setDescription("");
    setImages([]);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    if (images.length === 0) {
      toast.error("Please upload at least one photo.");
      return;
    }

    const priceNum = Number(price);
    const bedsNum = Number(beds);
    const bathsNum = Number(baths);
    const sqftNum = sqft.trim() === "" ? null : Number(sqft);

    if (!address.trim() || !description.trim()) {
      toast.error("Please fill in the address and description.");
      return;
    }
    if (!Number.isFinite(priceNum) || priceNum <= 0) {
      toast.error("Please enter a valid price.");
      return;
    }
    if (!Number.isFinite(bedsNum) || bedsNum < 0) {
      toast.error("Please enter a valid number of beds.");
      return;
    }
    if (!Number.isFinite(bathsNum) || bathsNum < 0) {
      toast.error("Please enter a valid number of baths.");
      return;
    }

    const payload: CreateListingRequest = {
      address: address.trim(),
      price: priceNum,
      beds: bedsNum,
      baths: bathsNum,
      sqft: sqftNum,
      description: description.trim(),
      image_urls: images.map((img) => img.path),
    };

    setSubmitting(true);
    try {
      const listing = await api.post<Listing>("/api/listings", payload);
      toast.success("Listing created!");
      resetForm();
      onCreated?.(listing);
    } catch (err) {
      if (err instanceof ApiError) {
        toast.error(
          typeof err.body === "object" && err.body && "detail" in err.body
            ? String((err.body as { detail: unknown }).detail)
            : "Failed to create listing."
        );
      } else {
        toast.error("Failed to create listing.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>New Listing</CardTitle>
        <CardDescription>
          Paste your listing details and upload photos to get started.
        </CardDescription>
      </CardHeader>
      <form onSubmit={handleSubmit}>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="address">Address</Label>
            <Input
              id="address"
              placeholder="123 Main St, Austin, TX 78701"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              disabled={submitting}
              required
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-4">
            <div className="space-y-2">
              <Label htmlFor="price">Price ($)</Label>
              <Input
                id="price"
                type="number"
                min="0"
                step="1000"
                placeholder="450000"
                value={price}
                onChange={(e) => setPrice(e.target.value)}
                disabled={submitting}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="beds">Beds</Label>
              <Input
                id="beds"
                type="number"
                min="0"
                step="1"
                placeholder="3"
                value={beds}
                onChange={(e) => setBeds(e.target.value)}
                disabled={submitting}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="baths">Baths</Label>
              <Input
                id="baths"
                type="number"
                min="0"
                step="0.5"
                placeholder="2"
                value={baths}
                onChange={(e) => setBaths(e.target.value)}
                disabled={submitting}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="sqft">Sqft</Label>
              <Input
                id="sqft"
                type="number"
                min="0"
                step="1"
                placeholder="1800"
                value={sqft}
                onChange={(e) => setSqft(e.target.value)}
                disabled={submitting}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              placeholder="Stunning 3-bed, 2-bath home with an open floor plan, updated kitchen, and a spacious backyard..."
              rows={5}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              disabled={submitting}
              required
            />
          </div>

          <div className="space-y-2">
            <Label>Photos</Label>
            <ImageUploader
              listingId={draftId}
              images={images}
              onChange={setImages}
              disabled={submitting}
            />
          </div>
        </CardContent>
        <CardFooter>
          <Button type="submit" disabled={submitting}>
            {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Create Listing
          </Button>
        </CardFooter>
      </form>
    </Card>
  );
}
