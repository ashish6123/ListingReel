import { redirect } from "next/navigation";

import { createClient } from "@/lib/supabase/server";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { BillingActions } from "@/components/billing-actions";
import { DashboardListings } from "@/components/dashboard-listings";
import type { User } from "@/types";

export default async function DashboardPage() {
  const supabase = createClient();
  const { data: authData } = await supabase.auth.getUser();

  if (!authData.user) {
    redirect("/login");
  }

  const { data: profile } = await supabase
    .from("users")
    .select("*")
    .eq("id", authData.user.id)
    .single<User>();

  const isPremium = profile?.is_premium ?? false;
  const videosUsed = profile?.videos_used_this_month ?? 0;
  const videoLimit = isPremium ? "Unlimited" : "3";
  const remaining = isPremium ? "Unlimited" : Math.max(0, 3 - videosUsed);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Welcome back{profile?.full_name ? `, ${profile.full_name}` : ""}.
          Create a new listing video below.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-start justify-between gap-2">
            <div>
              <CardDescription>Plan</CardDescription>
              <CardTitle>{isPremium ? "Pro" : "Free"}</CardTitle>
            </div>
            <BillingActions isPremium={isPremium} userEmail={authData.user.email ?? ""} />
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Videos used this month</CardDescription>
            <CardTitle>
              {videosUsed} / {videoLimit}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Videos remaining</CardDescription>
            <CardTitle>{remaining}</CardTitle>
          </CardHeader>
        </Card>
      </div>

      <DashboardListings />
    </div>
  );
}
