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
          {/* Agent Brand Icons */}
          <div className="flex items-center -space-x-1.5">
            {/* Claude / Anthropic Asterisk */}
            <span
              title="Claude Code & Desktop"
              className="w-5 h-5 rounded-full bg-[#D97706]/20 border border-[#D97706]/40 flex items-center justify-center text-[10px] text-[#F59E0B]"
            >
              ✳
            </span>
            {/* Cursor */}
            <span
              title="Cursor"
              className="w-5 h-5 rounded-full bg-[#3B82F6]/20 border border-[#3B82F6]/40 flex items-center justify-center text-[10px] text-[#60A5FA]"
            >
              ▲
            </span>
            {/* Windsurf */}
            <span
              title="Windsurf / Devin"
              className="w-5 h-5 rounded-full bg-[#06B6D4]/20 border border-[#06B6D4]/40 flex items-center justify-center text-[10px] text-[#22D3EE]"
            >
              ◈
            </span>
            {/* Antigravity / Gemini */}
            <span
              title="Antigravity / Gemini"
              className="w-5 h-5 rounded-full bg-[#10B981]/20 border border-[#10B981]/40 flex items-center justify-center text-[10px] text-[#34D399]"
            >
              ✦
            </span>
            {/* Copilot */}
            <span
              title="VS Code & Copilot"
              className="w-5 h-5 rounded-full bg-[#8B5CF6]/20 border border-[#8B5CF6]/40 flex items-center justify-center text-[10px] text-[#A78BFA]"
            >
              ●
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
