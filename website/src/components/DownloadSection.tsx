"use client";

import { useState, useEffect } from "react";
import { useOrigin } from "@/hooks/useOrigin";

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

  const copyToClipboard = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const platforms = {
    windows: {
      name: "Windows (x86_64 / ARM64)",
      badge: "Detected on your PC",
      icon: "🪟",
      binaryName: "learnloop.exe",
      downloadUrl: "https://github.com/Seife1/Devloop-Engine/releases/latest/download/learnloop-windows-x64.exe",
      size: "27.2 MB",
      description: "Standalone compiled single executable with embedded SQLite and migrations. Zero Python installation or dependencies required.",
      commands: [
        {
          label: "PowerShell (Recommended One-Liner)",
          cmd: `& ([scriptblock]::Create((iwr -useb "${origin}/setup.ps1").Content))`,
          hint: "Installs binary to ~/.learnloop/bin and auto-configures your active editor (Cursor, VS Code, Windsurf).",
        },
        {
          label: "Command Prompt (cmd.exe)",
          cmd: `powershell -NoProfile -ExecutionPolicy Bypass -Command "iwr -useb ${origin}/setup.ps1 | iex"`,
          hint: "Executes the installer script via Windows Command Prompt.",
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
      badge: "Universal Binary",
      icon: "🍎",
      binaryName: "learnloop-darwin",
      downloadUrl: "https://github.com/Seife1/Devloop-Engine/releases/latest/download/learnloop-darwin-universal",
      size: "24.8 MB",
      description: "Universal Mach-O binary compiled for M1/M2/M3/M4 Apple Silicon and Intel Macs.",
      commands: [
        {
          label: "Terminal (zsh / bash)",
          cmd: `curl -fsSL ${origin}/setup.sh | bash`,
          hint: "Installs to ~/.local/bin and automatically injects MCP config into Cursor and Claude Desktop.",
        },
        {
          label: "Manual Terminal Run",
          cmd: "chmod +x learnloop-darwin && mv learnloop-darwin /usr/local/bin/learnloop",
          hint: "Move the downloaded binary to your PATH manually.",
        },
      ],
    },
    linux: {
      name: "Linux (x86_64 & ARM64)",
      badge: "Linux ELF Binary",
      icon: "🐧",
      binaryName: "learnloop-linux-x64",
      downloadUrl: "https://github.com/Seife1/Devloop-Engine/releases/latest/download/learnloop-linux-x64",
      size: "23.5 MB",
      description: "Pre-compiled statically linked ELF binary for Ubuntu, Debian, Fedora, Arch, and Alpine.",
      commands: [
        {
          label: "Bash / Zsh (One-Liner)",
          cmd: `curl -fsSL ${origin}/setup.sh | bash`,
          hint: "Installs binary to ~/.local/bin and configures shell aliases.",
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

  return (
    <section id="download" className="py-24 px-6 bg-[#FCFCFD] text-[#0B0F19] border-t border-zinc-200 relative overflow-hidden">
      <div className="max-w-5xl mx-auto relative z-10">
        {/* Header */}
        <div className="text-center mb-14">
          <div className="text-xs font-mono uppercase tracking-[0.2em] text-emerald-600 mb-3 font-semibold">
            Zero-Dependency Distribution
          </div>
          <h2 className="text-3xl sm:text-5xl font-serif text-zinc-900 tracking-tight">
            Download LearnLoop. <span className="italic font-normal text-zinc-500">Ready in seconds.</span>
          </h2>
          <p className="text-xs sm:text-sm text-zinc-600 max-w-xl mx-auto font-sans leading-relaxed mt-4">
            Standalone single-file binaries compiled with PyInstaller. Zero Python runtime, zero PyPI packages, and zero external dependencies required on target workstations.
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
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6 mb-8 pb-8 border-b border-zinc-200">
            <div>
              <div className="inline-flex items-center gap-2 px-2.5 py-1 text-[10px] font-mono tracking-widest uppercase bg-emerald-50 text-emerald-800 border border-emerald-200 rounded-sm mb-3 font-semibold">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-600" />
                <span>{current.badge}</span>
              </div>
              <h3 className="text-2xl sm:text-3xl font-serif text-zinc-900">{current.name}</h3>
              <p className="text-xs text-zinc-600 mt-2 font-sans max-w-lg leading-relaxed">
                {current.description}
              </p>
            </div>

            <div className="flex flex-col sm:items-end justify-between gap-2 shrink-0">
              <a
                href={current.downloadUrl}
                download
                className="px-6 py-3.5 bg-[#0B0F19] hover:bg-emerald-600 text-white font-sans font-bold text-xs uppercase tracking-wider transition-all shadow-md rounded-lg text-center"
              >
                Download {current.binaryName}
              </a>
              <span className="text-[11px] font-mono text-zinc-500 text-center sm:text-right">
                {current.size} • SHA256 verified
              </span>
            </div>
          </div>

          {/* Shell Commands & Copy Boxes */}
          <div className="space-y-5">
            <div className="text-xs font-mono text-zinc-700 uppercase tracking-wider font-semibold">
              Available Command-Line Installation Options:
            </div>

            {current.commands.map((cmdItem, idx) => {
              const copyId = `${selectedPlatform}-${idx}`;
              const isCopied = copiedKey === copyId;
              return (
                <div key={idx} className="bg-zinc-50 border border-zinc-200/90 rounded-xl p-4">
                  <div className="flex items-center justify-between mb-1.5 text-[11px] font-mono">
                    <span className="text-zinc-800 font-bold">{cmdItem.label}</span>
                    <span className="text-[10px] text-zinc-500 hidden sm:inline">{cmdItem.hint}</span>
                  </div>

                  <div className="flex items-center justify-between font-mono text-xs text-zinc-200 gap-3 mt-2 bg-[#0B0F19] p-3 rounded-lg border border-zinc-800 shadow-inner">
                    <div className="flex items-center gap-2 overflow-x-auto scrollbar-none py-0.5">
                      <span className="text-emerald-400 font-bold select-none">&gt;</span>
                      <span className="select-all text-zinc-100 font-medium">{cmdItem.cmd}</span>
                    </div>

                    <button
                      onClick={() => copyToClipboard(cmdItem.cmd, copyId)}
                      className="shrink-0 px-3 py-1.5 bg-white/10 hover:bg-white/20 text-[10px] text-white tracking-wider uppercase font-semibold transition-colors rounded cursor-pointer"
                      title="Copy command"
                    >
                      {isCopied ? "COPIED ✓" : "COPY"}
                    </button>
                  </div>
                </div>
              );
            })}

            {/* Automatic Setup Callout */}
            <div className="p-3.5 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-900 flex items-start gap-2.5 font-sans mt-4">
              <span className="text-base leading-none">⚡</span>
              <div>
                <strong className="font-semibold">Automatic MCP Setup:</strong> Running any of the commands above automatically detects your active editor (Cursor, VS Code, Windsurf, Claude Desktop, Antigravity) and injects the MCP configuration directly. No manual JSON editing required.
              </div>
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
