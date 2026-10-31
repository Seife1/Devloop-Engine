"use client";

import { useState } from "react";
import { copyToClipboard } from "@/hooks/clipboard";

export default function CodeFlow() {
  const [copied, setCopied] = useState(false);

  const asciiDiagram = `+----------------------------------------------------------------------+
|                       IDE / CLIENT ENVIRONMENT                       |
|   Cursor  |  VS Code (Copilot/Cline)  |  Windsurf  |  Claude Desktop |
+----------------------------------+-----------------------------------+
                                   | (stdio / SSE / MCP 1.0)
                                   v
+----------------------------------------------------------------------+
|                        LEARNLOOP ENGINE CORE                         |
|                                                                      |
|   [ track_intent ]      [ manage_reviews ]    [ manage_knowledge ]   |
|   * Intent handshakes   * SM-2 intervals      * Concept taxonomy     |
|   * Tradeoff logs       * Daily briefing      * File linking         |
|                                                                      |
|                         [ explore_project ]                          |
|                         * Repo architecture tour                     |
|                         * Verified technical facts                   |
+-------------------+----------------------------------+---------------+
                    |                                  |
                    v                                  v
+-------------------------------------+  +-----------------------------+
|          LOCAL POST-COMMIT          |  |      ZERO-CONFIG SQLITE     |
|   Audits actual git commits         |  |      ~/.learnloop.db        |
|   Only verified code passes         |  |      or project .learn/     |
+-------------------------------------+  +-----------------------------+`;

  const handleCopy = async () => {
    const success = await copyToClipboard(asciiDiagram);
    if (success) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <section className="py-24 px-6 bg-[#0B0F19] text-[#FCFCFD] border-t border-white/10 relative overflow-hidden">
      {/* Ambient background glow behind diagram */}
      <div 
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[400px] bg-emerald-500/10 blur-[140px] pointer-events-none rounded-full" 
        aria-hidden="true" 
      />

      <div className="max-w-7xl mx-auto relative z-10">
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-10 gap-6">
          <div>
            <div className="text-xs font-mono uppercase tracking-[0.2em] text-emerald-400 mb-3 font-semibold flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              Universal Integration
            </div>
            <h2 className="text-3xl sm:text-5xl font-serif text-white tracking-tight">
              One protocol. <span className="italic font-normal text-zinc-300">Every editor on your machine.</span>
            </h2>
          </div>
          <p className="text-xs sm:text-sm text-zinc-400 max-w-md font-sans leading-relaxed">
            LearnLoop adheres strictly to the Model Context Protocol (MCP) standard. Running the installer or <code className="font-mono text-white bg-white/10 px-1.5 py-0.5 rounded font-semibold">learnloop init</code> automatically detects your active IDE and injects the MCP configuration—zero manual JSON editing required.
          </p>
        </div>

        {/* Diagram Card Container */}
        <div className="bg-[#0D1424]/90 border border-white/15 rounded-2xl p-4 sm:p-6 shadow-2xl backdrop-blur-xl transition-all">
          {/* Header Bar */}
          <div className="flex items-center justify-between pb-4 mb-4 border-b border-white/10">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-rose-500/80 inline-block" />
              <span className="w-3 h-3 rounded-full bg-amber-500/80 inline-block" />
              <span className="w-3 h-3 rounded-full bg-emerald-500/80 inline-block" />
              <span className="ml-2 font-mono text-[11px] text-zinc-400 tracking-wider uppercase font-semibold">
                MCP 1.0 Architecture Specification
              </span>
            </div>

            <button
              type="button"
              onClick={handleCopy}
              className="text-[11px] font-mono px-3 py-1 rounded-md bg-white/5 hover:bg-white/10 border border-white/10 text-zinc-300 hover:text-white transition-all flex items-center gap-1.5 cursor-pointer"
            >
              <span>{copied ? "✓ Copied" : "📋 Copy Spec"}</span>
            </button>
          </div>

          {/* Dedicated ASCII Spec Content */}
          <div className="bg-black/90 rounded-xl p-4 sm:p-6 overflow-x-auto border border-white/10 shadow-inner flex">
            <pre className="text-emerald-400 select-all font-mono whitespace-pre text-xs sm:text-sm leading-snug tracking-normal mx-auto w-fit [font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,'Courier_New',monospace]">
              {asciiDiagram}
            </pre>
          </div>
        </div>

        {/* Compatibility Matrix */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mt-8 pt-8 border-t border-white/10 text-center">
          <div className="p-3.5 border border-white/10 bg-[#111827] rounded-xl shadow-sm hover:border-emerald-500/30 transition-colors">
            <div className="text-sm font-serif text-white font-bold">Cursor</div>
            <div className="text-[11px] font-mono text-emerald-400 mt-1 font-medium">✓ Auto-configured</div>
          </div>
          <div className="p-3.5 border border-white/10 bg-[#111827] rounded-xl shadow-sm hover:border-emerald-500/30 transition-colors">
            <div className="text-sm font-serif text-white font-bold">VS Code & Cline</div>
            <div className="text-[11px] font-mono text-emerald-400 mt-1 font-medium">✓ Auto-configured</div>
          </div>
          <div className="p-3.5 border border-white/10 bg-[#111827] rounded-xl shadow-sm hover:border-emerald-500/30 transition-colors">
            <div className="text-sm font-serif text-white font-bold">Windsurf</div>
            <div className="text-[11px] font-mono text-emerald-400 mt-1 font-medium">✓ Auto-configured</div>
          </div>
          <div className="p-3.5 border border-white/10 bg-[#111827] rounded-xl shadow-sm hover:border-emerald-500/30 transition-colors">
            <div className="text-sm font-serif text-white font-bold">Claude Desktop</div>
            <div className="text-[11px] font-mono text-emerald-400 mt-1 font-medium">✓ Auto-configured</div>
          </div>
          <div className="p-3.5 border border-white/10 bg-[#111827] rounded-xl shadow-sm hover:border-emerald-500/30 transition-colors col-span-2 sm:col-span-1">
            <div className="text-sm font-serif text-white font-bold">Antigravity / Zed</div>
            <div className="text-[11px] font-mono text-emerald-400 mt-1 font-medium">✓ Auto-configured</div>
          </div>
        </div>
      </div>
    </section>
  );
}
