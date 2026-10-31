"use client";

import { useState } from "react";
import Link from "next/link";
import { useOrigin } from "@/hooks/useOrigin";
import { copyToClipboard } from "@/hooks/clipboard";

export default function AgentSetupCard() {
  const [copied, setCopied] = useState(false);
  const origin = useOrigin("https://learnloop.dev");

  const promptText = `Set up LearnLoop for me: ${origin}/prompt.md`;

  const copyPrompt = async () => {
    const success = await copyToClipboard(promptText);
    if (success) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto mt-12 p-6 sm:p-7 rounded-2xl bg-[#0e131f]/90 border border-white/10 shadow-[0_20px_50px_rgba(0,0,0,0.6)] backdrop-blur-md text-left">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2">
        <h2 className="text-xl sm:text-2xl font-serif font-bold text-white tracking-tight">
          Build with your favorite AI agent
        </h2>
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-mono uppercase tracking-wider bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 w-fit">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          Autonomous Setup
        </span>
      </div>

      <p className="text-xs sm:text-sm text-zinc-400 mb-6 leading-relaxed">
        Paste into any AI coding agent to install LearnLoop companion tooling globally:
      </p>

      {/* Pill Button Container matching the attached visual design */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
        <button
          onClick={copyPrompt}
          className="group relative inline-flex items-center justify-center gap-3 px-5 py-3 rounded-full bg-white/[0.06] hover:bg-white/[0.12] border border-white/15 hover:border-emerald-400/50 transition-all duration-200 text-white font-sans text-xs sm:text-sm font-medium shadow-sm hover:shadow-[0_0_20px_rgba(16,185,129,0.2)] active:scale-[0.98]"
        >
          {/* Official Agent Brand Icons Matching Cloudflare's Exact Design */}
          <div className="flex items-center -space-x-1.5">
            {/* Claude / Anthropic Official Sunburst / Asterisk SVG */}
            <span
              title="Claude Code & Claude Desktop"
              className="w-5 h-5 rounded-full bg-[#CC6B49]/15 border border-[#CC6B49]/40 flex items-center justify-center p-0.5 overflow-hidden shadow-sm backdrop-blur-sm"
            >
              <svg viewBox="0 0 24 24" fill="#D97757" className="w-3.5 h-3.5">
                <path d="M4.5 10.5C3.67 10.5 3 11.17 3 12s.67 1.5 1.5 1.5h15c.83 0 1.5-.67 1.5-1.5s-.67-1.5-1.5-1.5h-15zm2.74-5.24a1.5 1.5 0 00-2.12 2.12l10.6 10.6a1.5 1.5 0 002.12-2.12l-10.6-10.6zm10.6 0a1.5 1.5 0 00-2.12 0l-10.6 10.6a1.5 1.5 0 002.12 2.12l10.6-10.6a1.5 1.5 0 000-2.12zM12 3c-.83 0-1.5.67-1.5 1.5v15c0 .83.67 1.5 1.5 1.5s1.5-.67 1.5-1.5v-15C13.5 3.67 12.83 3 12 3z" />
              </svg>
            </span>

            {/* OpenAI / ChatGPT Swirl SVG */}
            <span
              title="OpenAI / ChatGPT / Codex"
              className="w-5 h-5 rounded-full bg-[#10A37F]/15 border border-[#10A37F]/40 flex items-center justify-center p-0.5 overflow-hidden shadow-sm backdrop-blur-sm"
            >
              <svg viewBox="0 0 24 24" fill="#10A37F" className="w-3 h-3">
                <path d="M22.28 9.53a5.98 5.98 0 0 0-.52-4.91 6.05 6.05 0 0 0-6.51-2.9A6.07 6.07 0 0 0 10.5.5a6.05 6.05 0 0 0-5.77 4.19 6.04 6.04 0 0 0-3.93 2.87 6.06 6.06 0 0 0 .74 7.07 5.98 5.98 0 0 0 .51 4.91 6.05 6.05 0 0 0 6.52 2.9A6.05 6.05 0 0 0 13.3 23.5a6.05 6.05 0 0 0 5.78-4.19 6.04 6.04 0 0 0 3.93-2.87 6.05 6.05 0 0 0-.73-6.91zm-8.99 12.44a4.54 4.54 0 0 1-2.92-1.06l.15-.08 4.88-2.82a.77.77 0 0 0 .39-.67v-6.88l2.07 1.2a.08.08 0 0 1 .04.06v5.7a4.56 4.56 0 0 1-4.61 4.55zm-8.8-3.95a4.55 4.55 0 0 1-.55-3.07l.15.09 4.88 2.82a.76.76 0 0 0 .77 0l5.96-3.44v2.39a.08.08 0 0 1-.03.07l-4.94 2.85a4.56 4.56 0 0 1-6.24-1.71zm-1.84-9.3a4.54 4.54 0 0 1 2.37-2l-.01.17v5.63a.76.76 0 0 0 .38.66l5.96 3.44-2.07 1.2a.08.08 0 0 1-.07 0l-4.94-2.85a4.56 4.56 0 0 1-1.62-6.25zM17.7 11.5l-5.96-3.44 2.07-1.2a.08.08 0 0 1 .07 0l4.94 2.85a4.56 4.56 0 0 1-1.12 8.24v-5.78a.76.76 0 0 0-.39-.67h.39zm3.56-2.58a4.54 4.54 0 0 1 .55 3.07l-.15-.09-4.88-2.82a.76.76 0 0 0-.77 0L10.05 12.5V10.1a.08.08 0 0 1 .03-.07l4.94-2.85a4.56 4.56 0 0 1 6.24 1.74zm-9.52-5.9a4.54 4.54 0 0 1 2.92 1.06l-.15.09-4.88 2.82a.76.76 0 0 0-.39.66v6.88l-2.07-1.2a.08.08 0 0 1-.04-.07v-5.7a4.56 4.56 0 0 1 4.61-4.54z" />
              </svg>
            </span>

            {/* Cursor Official Isometric Box SVG */}
            <span
              title="Cursor"
              className="w-5 h-5 rounded-full bg-white/10 border border-white/20 flex items-center justify-center p-0.5 overflow-hidden shadow-sm backdrop-blur-sm"
            >
              <svg viewBox="0 0 24 24" fill="none" className="w-3 h-3">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="#FFFFFF" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </span>

            {/* GitHub Copilot / Octocat Robot SVG */}
            <span
              title="GitHub Copilot & VS Code"
              className="w-5 h-5 rounded-full bg-[#8B5CF6]/15 border border-[#8B5CF6]/40 flex items-center justify-center p-0.5 overflow-hidden shadow-sm backdrop-blur-sm"
            >
              <svg viewBox="0 0 24 24" fill="#A78BFA" className="w-3.5 h-3.5">
                <path d="M12 2a10 10 0 0 0-3.16 19.49c.5.09.68-.22.68-.48v-1.7c-2.78.6-3.37-1.34-3.37-1.34-.45-1.16-1.11-1.47-1.11-1.47-.91-.62.07-.61.07-.61 1 .07 1.53 1.03 1.53 1.03.89 1.52 2.34 1.08 2.91.83.09-.65.35-1.09.63-1.34-2.22-.25-4.55-1.11-4.55-4.94 0-1.09.39-1.99 1.03-2.69-.1-.25-.45-1.27.1-2.65 0 0 .84-.27 2.75 1.02a9.58 9.58 0 0 1 5 0c1.91-1.29 2.75-1.02 2.75-1.02.55 1.38.2 2.4.1 2.65.64.7 1.03 1.6 1.03 2.69 0 3.84-2.34 4.68-4.57 4.93.36.31.68.92.68 1.85v2.74c0 .27.18.58.69.48A10 10 0 0 0 12 2z" />
              </svg>
            </span>
          </div>

          <span className="font-semibold text-zinc-100 group-hover:text-emerald-300 transition-colors">
            {copied ? "✓ Copied to Clipboard!" : "Copy prompt"}
          </span>

          <span className="text-[10px] font-mono text-zinc-400 bg-white/5 px-2 py-0.5 rounded border border-white/10 group-hover:border-white/20">
            {copied ? "Ready to paste" : "prompt.md"}
          </span>
        </button>

        <a
          href="/prompt.md"
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-zinc-400 hover:text-white transition-colors flex items-center justify-center gap-1.5 px-3 py-2"
        >
          <span>View raw instructions</span>
          <span className="text-zinc-600">›</span>
        </a>
      </div>

      <div className="mt-4 pt-4 border-t border-white/[0.06] flex flex-wrap items-center justify-between text-[11px] text-zinc-400 gap-2">
        <Link
          href="/docs"
          className="text-emerald-400 hover:text-emerald-300 font-medium inline-flex items-center gap-1 transition-colors"
        >
          Or follow a step-by-step guide for your agent
          <span>›</span>
        </Link>
        <span className="font-mono text-[10px] text-zinc-400">Zero-install • Powered by uvx</span>
      </div>
    </div>
  );
}
