"use client";

import { useState } from "react";
import { useOrigin } from "@/hooks/useOrigin";
import { copyToClipboard } from "@/hooks/clipboard";

export default function QuickstartCommands() {
  const origin = useOrigin("https://<your-host>");
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const copy = async (text: string, key: string) => {
    const success = await copyToClipboard(text);
    if (success) {
      setCopiedKey(key);
      setTimeout(() => setCopiedKey(null), 2000);
    }
  };

  const psCmd = `& ([scriptblock]::Create((iwr -useb "${origin}/setup.ps1").Content))`;
  const cmdCmd = `powershell -NoProfile -ExecutionPolicy Bypass -Command "iwr -useb ${origin}/setup.ps1 | iex"`;
  const shCmd = `curl -fsSL ${origin}/setup.sh | bash`;

  return (
    <div className="space-y-3 mb-6">
      <div className="bg-[#111827] border border-white/10 rounded-lg p-3.5 font-mono text-xs flex items-center justify-between group">
        <div className="overflow-x-auto pr-2">
          <div className="text-zinc-400 mb-1"># Windows PowerShell (One-liner installer)</div>
          <div className="text-emerald-400 select-all whitespace-nowrap">{psCmd}</div>
        </div>
        <button
          onClick={() => copy(psCmd, "ps")}
          className="shrink-0 text-[10px] tracking-wider uppercase px-2.5 py-1 rounded bg-white/5 hover:bg-white/15 text-zinc-300 transition-colors"
        >
          {copiedKey === "ps" ? "COPIED" : "COPY"}
        </button>
      </div>

      <div className="bg-[#111827] border border-white/10 rounded-lg p-3.5 font-mono text-xs flex items-center justify-between group">
        <div className="overflow-x-auto pr-2">
          <div className="text-zinc-400 mb-1"># Windows Command Prompt (CMD)</div>
          <div className="text-emerald-400 select-all whitespace-nowrap">{cmdCmd}</div>
        </div>
        <button
          onClick={() => copy(cmdCmd, "cmd")}
          className="shrink-0 text-[10px] tracking-wider uppercase px-2.5 py-1 rounded bg-white/5 hover:bg-white/15 text-zinc-300 transition-colors"
        >
          {copiedKey === "cmd" ? "COPIED" : "COPY"}
        </button>
      </div>

      <div className="bg-[#111827] border border-white/10 rounded-lg p-3.5 font-mono text-xs flex items-center justify-between group">
        <div className="overflow-x-auto pr-2">
          <div className="text-zinc-400 mb-1"># macOS & Linux Terminal (One-liner installer)</div>
          <div className="text-emerald-400 select-all whitespace-nowrap">{shCmd}</div>
        </div>
        <button
          onClick={() => copy(shCmd, "sh")}
          className="shrink-0 text-[10px] tracking-wider uppercase px-2.5 py-1 rounded bg-white/5 hover:bg-white/15 text-zinc-300 transition-colors"
        >
          {copiedKey === "sh" ? "COPIED" : "COPY"}
        </button>
      </div>
    </div>
  );
}
