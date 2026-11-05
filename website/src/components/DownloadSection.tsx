"use client";

import { useState, useEffect } from "react";
import { useOrigin } from "@/hooks/useOrigin";
import { copyToClipboard } from "@/hooks/clipboard";

type PlatformKey = "windows" | "macos" | "linux";

export default function DownloadSection() {
  const [selectedPlatform, setSelectedPlatform] = useState<PlatformKey>("windows");
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const origin = useOrigin("https://<your-host>");

  useEffect(() => {
    if (typeof window !== "undefined") {
      const userAgent = window.navigator.userAgent.toLowerCase();
      if (userAgent.includes("win")) {
        setSelectedPlatform("windows");
      } else if (userAgent.includes("mac")) {
        setSelectedPlatform("macos");
      } else if (userAgent.includes("linux")) {
        setSelectedPlatform("linux");
      }
    }
  }, []);

  const handleCopy = async (text: string, key: string) => {
    const success = await copyToClipboard(text);
    if (success) {
      setCopiedKey(key);
      setTimeout(() => setCopiedKey(null), 2000);
    }
  };

  const platforms = {
    windows: {
      name: "Windows (x86_64 / ARM64)",
      badge: "Detected on your PC",
      icon: "🪟",
      description: "Automated installer script. Automatically installs the standalone engine into ~/.learnloop/bin, sets up system PATH, and auto-configures your editors in Ghost Mode.",
      commands: [
        {
          label: "PowerShell (Recommended One-Liner)",
          cmd: `irm ${origin}/setup.ps1 | iex`,
          hint: "Installs binary to ~/.learnloop/bin and auto-configures active editors (Cursor, VS Code, Windsurf, Claude).",
        },
        {
          label: "Command Prompt (cmd.exe)",
          cmd: `powershell -c "irm ${origin}/setup.ps1 | iex"`,
          hint: "Executes the installer script directly via Windows Command Prompt.",
        },
        {
          label: "Git Bash / WSL",
          cmd: `curl -fsSL ${origin}/setup.sh | bash`,
          hint: "Installs Linux/WSL compatibility wrapper and hooks.",
        },
      ],
    },
    macos: {
      name: "macOS (Apple Silicon & Intel)",
      badge: "Universal Setup",
      icon: "🍎",
      description: "Zero-dependency installer. Automatically detects Apple Silicon (M1–M4) or Intel architecture, configures system PATH, and connects to your local IDEs.",
      commands: [
        {
          label: "Terminal (zsh / bash)",
          cmd: `curl -fsSL ${origin}/setup.sh | bash`,
          hint: "Installs to ~/.learnloop/bin and automatically configures editor MCP settings in Ghost Mode.",
        },
        {
          label: "Manual Run via Homebrew Python",
          cmd: "uv tool install git+https://github.com/Seife1/Devloop-Engine.git && learnloop init",
          hint: "Direct package install option for developers with uv or Python 3.11+ installed.",
        },
      ],
    },
    linux: {
      name: "Linux (x86_64 & ARM64)",
      badge: "Linux Shell Setup",
      icon: "🐧",
      description: "Automated installer for Ubuntu, Debian, Fedora, Arch, and Alpine. Detects environment, configures user profiles, and sets up IDE extensions with zero root permissions required.",
      commands: [
        {
          label: "Bash / Zsh (One-Liner)",
          cmd: `curl -fsSL ${origin}/setup.sh | bash`,
          hint: "Installs binary to ~/.learnloop/bin with resilient fallback and profile export.",
        },
        {
          label: "Daemon / Background Service",
          cmd: "learnloop dashboard --port 8765 &",
          hint: "Runs the local mission control dashboard in the background.",
        },
      ],
    },
  };

  const current = platforms[selectedPlatform];
  const heroCmd = current.commands[0];
  const isHeroCopied = copiedKey === `${selectedPlatform}-hero`;

  return (
    <section id="download" className="py-24 px-6 bg-[#FCFCFD] text-[#0B0F19] border-t border-zinc-200 relative overflow-hidden">
      <div className="max-w-5xl mx-auto relative z-10">
        {/* Header */}
        <div className="text-center mb-14">
          <div className="text-xs font-mono uppercase tracking-[0.2em] text-emerald-600 mb-3 font-semibold">
            Zero-Dependency Distribution
          </div>
          <h2 className="text-3xl sm:text-5xl font-serif text-zinc-900 tracking-tight">
            Install LearnLoop. <span className="italic font-normal text-zinc-500">Ready in seconds.</span>
          </h2>
          <p className="text-xs sm:text-sm text-zinc-600 max-w-xl mx-auto font-sans leading-relaxed mt-4">
            Zero workspace pollution. One terminal command installs the standalone engine, configures system PATH, and injects Ghost Mode MCP settings into your favorite editors.
          </p>
        </div>

        {/* Platform Selector Tabs */}
        <div className="flex items-center justify-center gap-3 mb-8 flex-wrap">
          {(Object.keys(platforms) as PlatformKey[]).map((key) => {
            const p = platforms[key];
            const isSelected = selectedPlatform === key;
            return (
              <button
                key={key}
                onClick={() => setSelectedPlatform(key)}
                className={`flex items-center gap-2 px-6 py-3 rounded-lg text-xs font-mono uppercase tracking-wider transition-all duration-200 border cursor-pointer ${
                  isSelected
                    ? "bg-[#0B0F19] text-white font-bold border-[#0B0F19] shadow-lg scale-[1.02]"
                    : "bg-white text-zinc-700 border-zinc-200 hover:border-zinc-400 hover:text-black shadow-sm"
                }`}
              >
                <span>{p.icon}</span>
                <span>{p.name.split(" ")[0]}</span>
              </button>
            );
          })}
        </div>

        {/* Main Platform Card */}
        <div className="border border-zinc-200 bg-white rounded-2xl p-8 sm:p-10 shadow-lg">
          {/* Card Header */}
          <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-6 mb-8 pb-8 border-b border-zinc-200">
            <div className="max-w-2xl">
              <div className="inline-flex items-center gap-2 px-2.5 py-1 text-[10px] font-mono tracking-widest uppercase bg-emerald-50 text-emerald-800 border border-emerald-200 rounded-sm mb-3 font-semibold">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-600" />
                <span>{current.badge}</span>
              </div>
              <h3 className="text-2xl sm:text-3xl font-serif text-zinc-900">{current.name}</h3>
              <p className="text-xs sm:text-sm text-zinc-600 mt-2 font-sans leading-relaxed">
                {current.description}
              </p>
            </div>

            <div className="flex items-center gap-2 px-3.5 py-2 bg-zinc-50 border border-zinc-200 rounded-lg text-[11px] font-mono text-zinc-600 shrink-0 self-start sm:self-auto shadow-sm">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span>100% Local • Zero Telemetry</span>
            </div>
          </div>

          {/* Hero Quick Install Command */}
          <div className="mb-8">
            <div className="bg-[#0B0F19] border border-zinc-800 rounded-2xl p-5 sm:p-7 shadow-xl relative overflow-hidden">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
                <div className="flex items-center gap-2">
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                    Recommended
                  </span>
                  <span className="text-xs font-mono font-bold text-zinc-100">
                    {heroCmd.label}
                  </span>
                </div>
                <span className="text-[11px] font-mono text-zinc-400">
                  ⚡ Ready in &lt; 5s • Zero Python Required
                </span>
              </div>

              <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3 bg-black/60 p-3.5 sm:p-4 rounded-xl border border-zinc-800 shadow-inner">
                <div className="flex items-center gap-3 overflow-x-auto scrollbar-none py-1 min-w-0">
                  <span className="text-emerald-400 font-bold select-none text-base">&gt;</span>
                  <span className="select-all text-zinc-100 font-mono text-xs sm:text-sm font-medium whitespace-nowrap">
                    {heroCmd.cmd}
                  </span>
                </div>

                <button
                  onClick={() => handleCopy(heroCmd.cmd, `${selectedPlatform}-hero`)}
                  className={`shrink-0 px-6 py-3 rounded-lg font-sans text-xs font-bold uppercase tracking-wider transition-all duration-200 cursor-pointer shadow-lg flex items-center justify-center gap-2 ${
                    isHeroCopied
                      ? "bg-emerald-500 text-white shadow-emerald-500/30 scale-[1.02]"
                      : "bg-emerald-600 hover:bg-emerald-500 text-white hover:scale-[1.02] shadow-emerald-900/40"
                  }`}
                  title="Copy command to clipboard"
                >
                  <span>{isHeroCopied ? "COPIED TO CLIPBOARD ✓" : "⚡ COPY INSTALL COMMAND"}</span>
                </button>
              </div>

              <div className="mt-3 flex items-center justify-between text-[11px] font-mono text-zinc-400">
                <span>{heroCmd.hint}</span>
                <span className="hidden sm:inline text-zinc-500">Run in terminal to install</span>
              </div>
            </div>
          </div>

          {/* Alternative Shell Commands (if more than 1) */}
          {current.commands.length > 1 && (
            <div className="space-y-4 pt-6 border-t border-zinc-100">
              <div className="text-xs font-mono text-zinc-700 uppercase tracking-wider font-semibold">
                Alternative Terminal Options:
              </div>

              <div className="grid grid-cols-1 gap-3">
                {current.commands.slice(1).map((cmdItem, idx) => {
                  const actualIdx = idx + 1;
                  const copyId = `${selectedPlatform}-${actualIdx}`;
                  const isCopied = copiedKey === copyId;
                  return (
                    <div key={actualIdx} className="bg-zinc-50 border border-zinc-200/90 rounded-xl p-3.5 sm:p-4">
                      <div className="flex items-center justify-between mb-1.5 text-[11px] font-mono">
                        <span className="text-zinc-800 font-bold">{cmdItem.label}</span>
                        <span className="text-[10px] text-zinc-500 hidden sm:inline">{cmdItem.hint}</span>
                      </div>

                      <div className="flex items-center justify-between font-mono text-xs text-zinc-200 gap-3 bg-[#0B0F19] p-2.5 sm:p-3 rounded-lg border border-zinc-800">
                        <div className="flex items-center gap-2 overflow-x-auto scrollbar-none py-0.5">
                          <span className="text-emerald-400 font-bold select-none">&gt;</span>
                          <span className="select-all text-zinc-100 font-medium whitespace-nowrap">{cmdItem.cmd}</span>
                        </div>

                        <button
                          onClick={() => handleCopy(cmdItem.cmd, copyId)}
                          className="shrink-0 px-3 py-1.5 bg-white/10 hover:bg-white/20 text-[10px] text-white tracking-wider uppercase font-semibold transition-colors rounded cursor-pointer"
                          title="Copy command"
                        >
                          {isCopied ? "COPIED ✓" : "COPY"}
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Automatic Setup Callout */}
          <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-900 flex items-start gap-2.5 font-sans mt-6">
            <span className="text-base leading-none">⚡</span>
            <div>
              <strong className="font-semibold">Automatic MCP Setup (Ghost Mode):</strong> Running the install command automatically detects your active editor (Cursor, VS Code, Windsurf, Claude Desktop, Antigravity) and injects the MCP configuration directly into your global user settings. Zero repository pollution and no manual JSON editing required.
            </div>
          </div>
        </div>

        {/* Bottom Security / Privacy Guarantee */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-8 text-center text-xs font-mono text-zinc-600">
          <div className="p-3.5 border border-zinc-200 bg-white rounded-lg shadow-sm">
            🔒 100% Local SQLite Storage
          </div>
          <div className="p-3.5 border border-zinc-200 bg-white rounded-lg shadow-sm">
            🚫 Zero Telemetry or External Sync
          </div>
          <div className="p-3.5 border border-zinc-200 bg-white rounded-lg shadow-sm">
            👻 Ghost Mode Zero Workspace Pollution
          </div>
        </div>
      </div>
    </section>
  );
}
