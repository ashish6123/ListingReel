import Link from "next/link";
import { redirect } from "next/navigation";
import {
  ArrowRight,
  CheckCircle2,
  Clock,
  Download,
  FileText,
  Mic,
  Video,
  Zap,
} from "lucide-react";

import { createClient } from "@/lib/supabase/server";

export default async function RootPage() {
  const supabase = createClient();
  const { data } = await supabase.auth.getUser();
  if (data.user) redirect("/dashboard");

  return (
    <div className="min-h-screen bg-white text-gray-900">
      {/* Nav */}
      <header className="sticky top-0 z-40 border-b border-gray-100 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <span className="text-xl font-bold tracking-tight">ListingReel</span>
          <nav className="flex items-center gap-4">
            <Link
              href="/login"
              className="text-sm text-gray-600 hover:text-gray-900"
            >
              Log in
            </Link>
            <Link
              href="/signup"
              className="rounded-lg bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-700"
            >
              Get started free
            </Link>
          </nav>
        </div>
      </header>

      {/* Hero */}
      <section className="mx-auto max-w-6xl px-6 pb-20 pt-24 text-center">
        <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-gray-200 bg-gray-50 px-4 py-1.5 text-sm text-gray-600">
          <Zap className="h-3.5 w-3.5 text-amber-500" />
          AI-powered · Ready in under 3 minutes
        </div>
        <h1 className="mx-auto max-w-3xl text-5xl font-bold leading-tight tracking-tight text-gray-900 sm:text-6xl">
          Turn any listing into a{" "}
          <span className="text-indigo-600">scroll-stopping Reel</span>
        </h1>
        <p className="mx-auto mt-6 max-w-xl text-lg text-gray-500">
          Paste your listing details, upload photos — ListingReel writes the
          script, records the voiceover, and assembles the video. Ready to post
          on Instagram, TikTok, or YouTube Shorts.
        </p>
        <div className="mt-10 flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
          <Link
            href="/signup"
            className="flex items-center gap-2 rounded-lg bg-indigo-600 px-6 py-3 text-base font-semibold text-white shadow-sm hover:bg-indigo-500"
          >
            Generate your first video free
            <ArrowRight className="h-4 w-4" />
          </Link>
          <span className="text-sm text-gray-400">
            No credit card required · 3 free videos/month
          </span>
        </div>

        {/* Mockup */}
        <div className="mx-auto mt-16 max-w-4xl overflow-hidden rounded-2xl border border-gray-200 bg-gray-50 shadow-xl">
          <div className="flex items-center gap-2 border-b border-gray-200 bg-white px-4 py-3">
            <div className="h-3 w-3 rounded-full bg-red-400" />
            <div className="h-3 w-3 rounded-full bg-amber-400" />
            <div className="h-3 w-3 rounded-full bg-green-400" />
            <span className="ml-2 text-xs text-gray-400">ListingReel Dashboard</span>
          </div>
          <div className="grid grid-cols-3 gap-4 p-6">
            {[
              { label: "742 Evergreen Terrace", status: "Ready", color: "bg-green-100 text-green-800" },
              { label: "88 Marina Tower, Dubai", status: "Processing", color: "bg-blue-100 text-blue-800" },
              { label: "14 Kensington Rd, London", status: "Ready", color: "bg-green-100 text-green-800" },
            ].map((item) => (
              <div key={item.label} className="overflow-hidden rounded-xl border border-gray-200 bg-white text-left">
                <div className="aspect-video bg-gradient-to-br from-gray-200 to-gray-300" />
                <div className="p-3">
                  <p className="truncate text-xs font-medium text-gray-700">{item.label}</p>
                  <span className={`mt-1 inline-block rounded-full px-2 py-0.5 text-xs font-medium ${item.color}`}>
                    {item.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Social proof strip */}
      <section className="border-y border-gray-100 bg-gray-50 py-6">
        <div className="mx-auto max-w-6xl px-6 text-center">
          <p className="text-sm font-medium text-gray-500">
            Built for agents in{" "}
            <span className="text-gray-800">Dubai · Austin · London · Toronto · Sydney</span>
          </p>
        </div>
      </section>

      {/* How it works */}
      <section className="mx-auto max-w-6xl px-6 py-24">
        <div className="mb-14 text-center">
          <h2 className="text-3xl font-bold tracking-tight">
            Three steps. Done in minutes.
          </h2>
          <p className="mt-3 text-gray-500">
            No video editing. No voiceover recording. No design skills.
          </p>
        </div>
        <div className="grid gap-8 sm:grid-cols-3">
          {[
            {
              icon: <FileText className="h-6 w-6 text-indigo-600" />,
              step: "01",
              title: "Paste your listing",
              desc: "Add the address, price, beds, baths, description, and up to 10 property photos.",
            },
            {
              icon: <Mic className="h-6 w-6 text-indigo-600" />,
              step: "02",
              title: "AI does the work",
              desc: "We write a 30-second script, record a professional voiceover, and assemble the video — automatically.",
            },
            {
              icon: <Download className="h-6 w-6 text-indigo-600" />,
              step: "03",
              title: "Download & post",
              desc: "Get a 1080×1920 MP4 ready for Instagram Reels, TikTok, or YouTube Shorts.",
            },
          ].map((item) => (
            <div key={item.step} className="rounded-2xl border border-gray-200 p-8">
              <div className="mb-4 flex items-center justify-between">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-50">
                  {item.icon}
                </div>
                <span className="text-3xl font-bold text-gray-100">{item.step}</span>
              </div>
              <h3 className="mb-2 text-lg font-semibold">{item.title}</h3>
              <p className="text-sm leading-relaxed text-gray-500">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="bg-gray-50 py-24">
        <div className="mx-auto max-w-6xl px-6">
          <div className="mb-14 text-center">
            <h2 className="text-3xl font-bold tracking-tight">
              Everything an agent needs
            </h2>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[
              { title: "AI-written scripts", desc: "Groq-powered scripts tailored to each listing's unique features." },
              { title: "Natural voiceover", desc: "ElevenLabs AI voice — sounds human, not robotic." },
              { title: "Ken Burns transitions", desc: "Cinematic pan and zoom across your listing photos." },
              { title: "Burned-in captions", desc: "Captions sync with the voiceover for silent-scroll viewers." },
              { title: "Vertical format", desc: "1080×1920 — native format for Instagram, TikTok, YouTube Shorts." },
              { title: "Instant download", desc: "MP4 ready in your hands in under 3 minutes." },
            ].map((f) => (
              <div key={f.title} className="flex gap-3 rounded-xl bg-white p-5 shadow-sm">
                <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-indigo-500" />
                <div>
                  <p className="font-semibold">{f.title}</p>
                  <p className="mt-0.5 text-sm text-gray-500">{f.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section className="mx-auto max-w-6xl px-6 py-24">
        <div className="mb-14 text-center">
          <h2 className="text-3xl font-bold tracking-tight">Simple pricing</h2>
          <p className="mt-3 text-gray-500">Start free. Upgrade when you need more.</p>
        </div>
        <div className="mx-auto grid max-w-3xl gap-6 sm:grid-cols-2">
          {/* Free */}
          <div className="rounded-2xl border border-gray-200 p-8">
            <p className="text-sm font-semibold uppercase tracking-widest text-gray-500">Free</p>
            <p className="mt-3 text-4xl font-bold">$0</p>
            <p className="mt-1 text-sm text-gray-400">forever</p>
            <ul className="mt-8 space-y-3 text-sm text-gray-600">
              {["3 videos per month", "All AI features included", "1080×1920 MP4 download", "Standard processing speed"].map((f) => (
                <li key={f} className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 shrink-0 text-gray-400" />
                  {f}
                </li>
              ))}
            </ul>
            <Link
              href="/signup"
              className="mt-8 block rounded-lg border border-gray-900 px-4 py-2.5 text-center text-sm font-semibold text-gray-900 hover:bg-gray-50"
            >
              Get started free
            </Link>
          </div>

          {/* Pro */}
          <div className="relative rounded-2xl bg-indigo-600 p-8 text-white shadow-lg">
            <div className="absolute right-6 top-6 rounded-full bg-white/20 px-3 py-0.5 text-xs font-semibold">
              Most popular
            </div>
            <p className="text-sm font-semibold uppercase tracking-widest text-indigo-200">Pro</p>
            <p className="mt-3 text-4xl font-bold">$19</p>
            <p className="mt-1 text-sm text-indigo-300">per month</p>
            <ul className="mt-8 space-y-3 text-sm text-indigo-100">
              {[
                "Unlimited videos per month",
                "All AI features included",
                "1080×1920 MP4 download",
                "Priority processing speed",
                "Early access to new features",
              ].map((f) => (
                <li key={f} className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 shrink-0 text-white/70" />
                  {f}
                </li>
              ))}
            </ul>
            <Link
              href="/signup"
              className="mt-8 block rounded-lg bg-white px-4 py-2.5 text-center text-sm font-semibold text-indigo-600 hover:bg-indigo-50"
            >
              Start with Pro
            </Link>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="bg-gray-50 py-24">
        <div className="mx-auto max-w-2xl px-6">
          <h2 className="mb-10 text-center text-3xl font-bold tracking-tight">
            Frequently asked questions
          </h2>
          <div className="space-y-6">
            {[
              {
                q: "Do I need any video editing skills?",
                a: "None at all. You paste your listing details and upload photos — the rest is fully automated.",
              },
              {
                q: "How long does it take to generate a video?",
                a: "Typically 2–4 minutes from listing submission to downloadable MP4.",
              },
              {
                q: "What format is the output video?",
                a: "1080×1920 MP4 (vertical), ready to upload directly to Instagram Reels, TikTok, or YouTube Shorts.",
              },
              {
                q: "Can I use my own photos?",
                a: "Yes — upload up to 10 photos per listing. ListingReel uses them as the visual backdrop of the video.",
              },
              {
                q: "What does the AI voiceover sound like?",
                a: "We use ElevenLabs — one of the most natural-sounding AI voice engines available. It sounds professional, not robotic.",
              },
            ].map((item) => (
              <div key={item.q} className="rounded-xl bg-white p-6 shadow-sm">
                <p className="font-semibold text-gray-900">{item.q}</p>
                <p className="mt-2 text-sm leading-relaxed text-gray-500">{item.a}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="mx-auto max-w-6xl px-6 py-24 text-center">
        <div className="rounded-3xl bg-indigo-600 px-8 py-16">
          <div className="mb-4 flex justify-center">
            <Clock className="h-8 w-8 text-indigo-300" />
          </div>
          <h2 className="text-3xl font-bold text-white">
            Your next listing video takes 3 minutes.
          </h2>
          <p className="mx-auto mt-4 max-w-md text-indigo-200">
            Join agents in Dubai, Austin, and London who are posting daily
            listing Reels without touching a video editor.
          </p>
          <Link
            href="/signup"
            className="mt-8 inline-flex items-center gap-2 rounded-lg bg-white px-6 py-3 text-base font-semibold text-indigo-600 shadow hover:bg-indigo-50"
          >
            Generate your first video free
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-100 py-8">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-6 sm:flex-row">
          <span className="text-sm font-semibold">ListingReel</span>
          <div className="flex gap-6 text-sm text-gray-500">
            <Link href="/login" className="hover:text-gray-900">Log in</Link>
            <Link href="/signup" className="hover:text-gray-900">Sign up</Link>
          </div>
          <p className="text-xs text-gray-400">© {new Date().getFullYear()} ListingReel. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
