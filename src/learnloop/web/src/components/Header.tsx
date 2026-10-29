"use client";

import { useState, useRef, useEffect } from "react";
import Logo from "@/components/Logo";

export interface ProjectInfo {
  id: string;
  name: string;
  folder: string;
  headline?: string;
  score?: number;
  stale_count?: number;
  due_count?: number;
  queue_waiting?: number;
  last_activity?: string;
}

interface HeaderProps {
  isHealthy: boolean;
  version: string;
  toolsCount: number;
  dbPath: string | null;
  projects: ProjectInfo[];
  selectedProjectId: string;
  onSelectProject: (id: string) => void;
  onRefresh: () => void;
}

export default function Header({
  isHealthy,
  version,
  toolsCount,
  dbPath,
  projects,
  selectedProjectId,
  onSelectProject,
  onRefresh,
}: HeaderProps) {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const activeProject = projects.find((p) => p.id === selectedProjectId) || projects[0];

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <header className="border-b border-white/10 bg-[#0B0F19]/95 backdrop-blur sticky top-0 z-40 px-6 py-3">
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
        {/* Left: Brand + Project Switcher */}
        <div className="flex items-center gap-5">
          <a href="/" className="flex items-center gap-2 hover:opacity-90 transition-opacity">
            <Logo variant="dark" size="md" />
          </a>

          {/* Project Switcher Dropdown */}
          <div className="relative" ref={dropdownRef}>
            <button
              onClick={() => setDropdownOpen(!dropdownOpen)}
              className="flex items-center gap-2.5 px-3 py-1.5 bg-[#121826] hover:bg-[#1A2234] border border-white/10 rounded-md text-xs font-mono text-white transition-all cursor-pointer"
              title="Switch Workspace Project"
            >
              <span className="text-[#94A3B8]">Repo:</span>
              <span className="font-semibold text-emerald-300 max-w-[140px] sm:max-w-[200px] truncate">
                {activeProject ? activeProject.name : "Select Project"}
              </span>
              <span className="text-[10px] text-[#71717A] bg-white/5 px-1.5 py-0.5 rounded">
                {projects.length}
              </span>
              <span className="text-[10px] text-[#94A3B8]">▾</span>
            </button>

            {dropdownOpen && (
              <div className="absolute left-0 top-full mt-1.5 w-72 bg-[#121826] border border-white/15 rounded-lg shadow-2xl py-1.5 z-50 overflow-hidden">
                <div className="px-3 py-1.5 border-b border-white/5 text-[10px] font-mono uppercase tracking-wider text-[#94A3B8]">
                  Registered Projects ({projects.length})
                </div>
                <div className="max-h-64 overflow-y-auto divide-y divide-white/5">
                  {projects.map((p) => {
                    const isSelected = p.id === selectedProjectId;
                    return (
                      <button
                        key={p.id}
                        onClick={() => {
                          onSelectProject(p.id);
                          setDropdownOpen(false);
                        }}
                        className={`w-full text-left px-3 py-2.5 text-xs transition-colors flex items-center justify-between cursor-pointer ${
                          isSelected
                            ? "bg-emerald-500/10 text-emerald-300 font-medium"
                            : "text-[#FCFCFD] hover:bg-white/5"
                        }`}
                      >
                        <div className="truncate pr-2">
                          <div className="font-sans font-medium text-xs truncate">
                            {p.name}
                          </div>
                          <div className="font-mono text-[10px] text-[#71717A] truncate">
                            {p.folder}
                          </div>
                        </div>
                        {isSelected && (
                          <span className="text-[10px] font-mono px-1.5 py-0.5 bg-emerald-500/20 text-emerald-300 rounded shrink-0">
                            Active
                          </span>
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          {/* Health indicator */}
          <div className="hidden lg:flex items-center gap-2 pl-4 border-l border-white/10 text-xs font-mono">
            <span
              className={`w-2 h-2 rounded-full ${
                isHealthy ? "bg-emerald-400 animate-pulse" : "bg-rose-500"
              }`}
            />
            <span className={isHealthy ? "text-emerald-300" : "text-rose-400"}>
              {isHealthy ? "127.0.0.1:8765" : "OFFLINE"}
            </span>
          </div>
        </div>

        {/* Right: Quick metadata & Ping */}
        <div className="flex items-center gap-3 text-xs font-mono">
          <div className="hidden md:flex items-center gap-3 text-[#94A3B8]">
            <span>MCP 4 Clusters</span>
            {dbPath && (
              <>
                <span>•</span>
                <span className="truncate max-w-[160px]" title={dbPath}>
                  {dbPath.split(/[\\/]/).pop()}
                </span>
              </>
            )}
          </div>

          <button
            onClick={onRefresh}
            className="px-2.5 py-1 bg-white/5 hover:bg-white/10 border border-white/10 text-xs text-white rounded transition-colors"
            title="Refresh database & git status"
          >
            ↻ Ping
          </button>
        </div>
      </div>
    </header>
  );
}
