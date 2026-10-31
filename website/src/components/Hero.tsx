"use client";

import Link from "next/link";
import AgentSetupCard from "./AgentSetupCard";

export default function Hero() {
  return (
    <section className="relative bg-[#FCFCFD] text-[#FCFCFD] pt-36 pb-32 px-6 overflow-hidden">
      {/* Background dark canvas + grid with the exact Image 1 curvy gradient mask (isolated from content) */}
      <div className="absolute inset-0 bg-[#0B0F19] hero-grid pointer-events-none">
        {/* Decorative hairline vertical grid guides */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-full border-x border-white/[0.04] pointer-events-none" />
      </div>

      <div className="relative z-10 max-w-4xl mx-auto text-center flex flex-col items-center">
        {/* Badge */}
        <div className="inline-flex items-center gap-2.5 px-3.5 py-1.5 rounded-full border border-white/10 bg-white/[0.03] text-[11px] font-mono tracking-widest uppercase text-[#A1A1AA] mb-8 shadow-sm">
          <span className="w-1.5 h-1.5 rounded-full bg-[#10B981] pulse-dot" />
          <span>MCP Server Engine • 4 Domain Clusters</span>
          <span className="text-white/40">›</span>
          <span className="text-emerald-400 font-semibold">v1.0 Ready</span>
        </div>

        {/* Main Headline */}
        <h1 className="text-4xl sm:text-6xl md:text-7xl font-serif tracking-tight leading-[1.08] mb-8 text-white">
          Learn<span className="italic font-normal text-zinc-300">Loop</span>
        </h1>

        <p className="max-w-2xl text-lg sm:text-xl md:text-2xl font-serif italic text-zinc-300 font-normal leading-relaxed mb-8">
          "Close the gap between what AI builds and what you can defend."
        </p>

        {/* Value explanation */}
        <p className="max-w-xl text-sm sm:text-base text-zinc-200 font-sans leading-relaxed mb-4">
          An autonomous cognitive sidecar that connects to AI IDEs & Editors. It silently tracks architectural decisions, maintains your knowledge catalog, and tests your mastery through spaced repetition.
        </p>

        {/* Build with your favorite AI agent card */}
        <AgentSetupCard />

        {/* Elevated Frosted Dark Glass Dock - Sharp, Focused CTA Buttons over Curve */}
        <div className="mt-10 inline-flex flex-col sm:flex-row items-center gap-3 sm:gap-4 p-2 sm:p-2.5 rounded-2xl bg-[#0B0F19] border border-white/20 shadow-[0_20px_50px_rgba(0,0,0,0.5)]">
          <Link
            href="/#download"
            className="w-full sm:w-auto px-7 py-3.5 bg-white text-[#0B0F19] font-sans font-semibold text-xs tracking-wider uppercase hover:bg-emerald-400 hover:text-black transition-all duration-200 shadow-md rounded-xl text-center"
          >
            Download Binary (.exe / .sh)
          </Link>

          <Link
            href="/docs"
            className="w-full sm:w-auto px-7 py-3.5 bg-white/10 hover:bg-white/20 border border-white/20 text-white font-sans font-medium text-xs tracking-wider uppercase transition-all duration-200 rounded-xl text-center"
          >
            Read Specification
          </Link>
        </div>
      </div>
    </section>
  );
}
