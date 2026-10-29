"use client";

import { useEffect, useState } from "react";

export interface KnowledgeItem {
  id?: string;
  key: string;
  title: string;
  band: string;
  depth: number;
  status: string;
  is_stale?: boolean;
  drift_commits_count?: number;
  files: string[];
  summary: string;
}

interface KnowledgeCatalogProps {
  projectId?: string;
  serverUrl?: string;
}

export default function KnowledgeCatalog({
  projectId,
  serverUrl = "",
}: KnowledgeCatalogProps) {
  const [items, setItems] = useState<KnowledgeItem[]>([]);
  const [markdown, setMarkdown] = useState<string>("");
  const [viewMode, setViewMode] = useState<"table" | "markdown">("table");
  const [filterBand, setFilterBand] = useState<string>("all");
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    async function fetchConcepts() {
      if (!projectId) return;
      setLoading(true);
      try {
        const res = await fetch(`${serverUrl}/api/projects/${projectId}/concepts`);
        if (res.ok) {
          const data = await res.json();
          if (data.items) {
            setItems(data.items);
          }
          if (data.markdown) {
            setMarkdown(data.markdown);
          }
        }
      } catch (err) {
        console.error("Error loading concepts:", err);
      } finally {
        setLoading(false);
      }
    }
    fetchConcepts();
  }, [projectId, serverUrl]);

  const copyPrompt = (prompt: string, feedback: string) => {
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(prompt);
      setToast(feedback);
      setTimeout(() => setToast(null), 3000);
    }
  };

  const staleCount = items.filter((i) => i.is_stale || i.status === "stale").length;
  const coreCount = items.filter((i) => i.band === "core").length;
  const periphCount = items.filter((i) => i.band === "periphery").length;
  const advCount = items.filter((i) => i.band === "advanced").length;

  const filtered = items.filter((item) => {
    const isStale = Boolean(item.is_stale || item.status === "stale");
    const matchesBand =
      filterBand === "all"
        ? true
        : filterBand === "stale"
        ? isStale
        : item.band === filterBand;

    const matchesSearch =
      item.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.key.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.summary.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesBand && matchesSearch;
  });

  return (
    <div className="bg-[#121826] border border-white/10 rounded-xl p-6 relative">
      {/* Toast Notification */}
      {toast && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 bg-emerald-500 text-black px-4 py-2 rounded-lg font-mono text-xs font-bold shadow-2xl flex items-center gap-2 animate-bounce">
          <span>✓</span>
          <span>{toast}</span>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6 pb-4 border-b border-white/10">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[10px] font-mono tracking-widest uppercase text-[#94A3B8]">
              Architectural Invariants & Drift Detection
            </span>
            {staleCount > 0 && (
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-rose-500/20 text-rose-300 border border-rose-500/30">
                {staleCount} Stale Invariant{staleCount > 1 ? "s" : ""}
              </span>
            )}
          </div>
          <h2 className="text-xl font-serif text-white tracking-tight">
            Concept Knowledge Base
          </h2>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono">
          <button
            onClick={() => setViewMode("table")}
            className={`px-3 py-1.5 rounded transition-all cursor-pointer ${
              viewMode === "table"
                ? "bg-blue-500/20 text-blue-300 border border-blue-500/40 font-medium"
                : "text-[#94A3B8] hover:text-white border border-transparent"
            }`}
          >
            Catalog Table ({items.length})
          </button>
          <button
            onClick={() => setViewMode("markdown")}
            className={`px-3 py-1.5 rounded transition-all cursor-pointer ${
              viewMode === "markdown"
                ? "bg-blue-500/20 text-blue-300 border border-blue-500/40 font-medium"
                : "text-[#94A3B8] hover:text-white border border-transparent"
            }`}
          >
            Raw Concept Log (.md)
          </button>
        </div>
      </div>

      {/* Pro Tip: Interactive IDE Sparring Callout */}
      <div className="mb-6 p-4 rounded-lg bg-gradient-to-r from-blue-500/10 via-purple-500/10 to-transparent border border-blue-500/20 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-start gap-3">
          <span className="text-lg">⚔️</span>
          <div>
            <div className="font-serif font-bold text-xs sm:text-sm text-white">
              Learning is 10x more effective inside your IDE
            </div>
            <div className="text-xs text-[#94A3B8] mt-0.5 font-sans leading-relaxed">
              Your AI assistant (Cursor, Windsurf, VS Code, Antigravity) has full access to your codebase diffs. Use <code className="text-purple-300 bg-purple-500/10 px-1.5 py-0.5 rounded font-mono">/interview</code> in chat to defend any concept or invariant aloud!
            </div>
          </div>
        </div>
        <button
          onClick={() => copyPrompt("/interview on my project's architecture and recent commits", "Copied '/interview' prompt! Paste into your IDE chat.")}
          className="shrink-0 px-3 py-1.5 bg-white/10 hover:bg-white/20 border border-white/15 text-white font-mono text-xs rounded transition-colors cursor-pointer text-center"
        >
          Copy IDE Prompt 📋
        </button>
      </div>

      {viewMode === "table" ? (
        <div>
          {/* Controls & Filter Bar */}
          <div className="flex flex-col sm:flex-row gap-4 mb-6">
            <input
              type="text"
              placeholder="Search concepts, keys, or summaries..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="flex-1 bg-black/40 border border-white/10 rounded-lg px-4 py-2 text-xs font-mono text-white placeholder-[#71717A] focus:outline-none focus:border-blue-500"
            />
            <div className="flex items-center gap-1.5 text-xs font-mono flex-wrap">
              <span className="text-[#94A3B8] mr-1">Filter:</span>
              <button
                onClick={() => setFilterBand("all")}
                className={`px-2.5 py-1 rounded transition-all cursor-pointer ${
                  filterBand === "all"
                    ? "bg-white/15 text-white font-medium border border-white/20"
                    : "text-[#94A3B8] hover:text-white"
                }`}
              >
                All ({items.length})
              </button>
              {staleCount > 0 && (
                <button
                  onClick={() => setFilterBand("stale")}
                  className={`px-2.5 py-1 rounded transition-all cursor-pointer flex items-center gap-1 ${
                    filterBand === "stale"
                      ? "bg-rose-500/25 text-rose-200 border border-rose-500/50 font-bold"
                      : "bg-rose-500/10 text-rose-300 border border-rose-500/20 hover:bg-rose-500/20"
                  }`}
                >
                  <span>⚠️ Stale</span>
                  <span>({staleCount})</span>
                </button>
              )}
              <button
                onClick={() => setFilterBand("core")}
                className={`px-2.5 py-1 rounded capitalize transition-all cursor-pointer ${
                  filterBand === "core"
                    ? "bg-white/15 text-white font-medium border border-white/20"
                    : "text-[#94A3B8] hover:text-white"
                }`}
              >
                Core ({coreCount})
              </button>
              <button
                onClick={() => setFilterBand("periphery")}
                className={`px-2.5 py-1 rounded capitalize transition-all cursor-pointer ${
                  filterBand === "periphery"
                    ? "bg-white/15 text-white font-medium border border-white/20"
                    : "text-[#94A3B8] hover:text-white"
                }`}
              >
                Periphery ({periphCount})
              </button>
              <button
                onClick={() => setFilterBand("advanced")}
                className={`px-2.5 py-1 rounded capitalize transition-all cursor-pointer ${
                  filterBand === "advanced"
                    ? "bg-white/15 text-white font-medium border border-white/20"
                    : "text-[#94A3B8] hover:text-white"
                }`}
              >
                Advanced ({advCount})
              </button>
            </div>
          </div>

          {/* Table */}
          {loading ? (
            <div className="py-8 text-center text-xs font-mono text-[#94A3B8]">
              Loading concepts from SQLite...
            </div>
          ) : filtered.length === 0 ? (
            <div className="py-12 text-center text-xs font-mono text-[#71717A]">
              {filterBand === "stale"
                ? "✨ All concepts are in sync with your Git commits!"
                : "No concepts matching filter."}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono border-collapse">
                <thead>
                  <tr className="border-b border-white/10 text-[#94A3B8] text-[11px] uppercase tracking-wider">
                    <th className="py-3 px-4">Concept Key</th>
                    <th className="py-3 px-4">Title & Invariant</th>
                    <th className="py-3 px-4">Sync Status</th>
                    <th className="py-3 px-4">Band & Depth</th>
                    <th className="py-3 px-4">Files Tracked</th>
                    <th className="py-3 px-4 text-right">Spar in IDE</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {filtered.map((item) => {
                    const isStale = Boolean(item.is_stale || item.status === "stale");
                    return (
                      <tr
                        key={item.key}
                        className={`hover:bg-white/[0.02] transition-colors ${
                          isStale ? "bg-rose-500/[0.03]" : ""
                        }`}
                      >
                        <td className="py-3.5 px-4 font-bold text-blue-300">
                          {item.key}
                        </td>
                        <td className="py-3.5 px-4">
                          <div className="font-sans font-semibold text-white text-[13px] mb-0.5">
                            {item.title}
                          </div>
                          <div className="font-sans text-[#94A3B8] text-xs leading-relaxed max-w-xl">
                            {item.summary}
                          </div>
                        </td>
                        <td className="py-3.5 px-4 whitespace-nowrap">
                          {isStale ? (
                            <span
                              className="px-2 py-0.5 rounded text-[10px] font-mono bg-rose-500/20 text-rose-300 border border-rose-500/30 inline-flex items-center gap-1.5"
                              title="Code in tracked files was modified after this concept was registered."
                            >
                              <span>⚠️ STALE</span>
                              {item.drift_commits_count ? (
                                <span className="opacity-80">
                                  (+{item.drift_commits_count} commits)
                                </span>
                              ) : null}
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">
                              ✓ In Sync
                            </span>
                          )}
                        </td>
                        <td className="py-3.5 px-4 whitespace-nowrap">
                          <div className="flex items-center gap-2">
                            <span className="px-2 py-0.5 rounded text-[10px] uppercase font-mono bg-purple-500/10 text-purple-300 border border-purple-500/20">
                              {item.band}
                            </span>
                            <span className="text-[#94A3B8] text-[11px]">
                              {item.depth}/5
                            </span>
                          </div>
                        </td>
                        <td className="py-3.5 px-4">
                          <div className="flex flex-wrap gap-1 max-w-xs">
                            {item.files.map((f, i) => (
                              <span
                                key={i}
                                className="px-1.5 py-0.5 bg-white/5 border border-white/5 rounded text-[10px] text-[#94A3B8] truncate max-w-[140px]"
                                title={f}
                              >
                                {f.split(/[\\/]/).pop()}
                              </span>
                            ))}
                          </div>
                        </td>
                        <td className="py-3.5 px-4 text-right whitespace-nowrap">
                          <button
                            onClick={() =>
                              copyPrompt(
                                `/interview on concept '${item.key}' (${item.title})`,
                                `Copied '/interview on ${item.key}'! Paste into your IDE chat.`
                              )
                            }
                            className="px-2.5 py-1 bg-white/5 hover:bg-purple-600 hover:text-white border border-white/10 text-zinc-300 rounded font-mono text-[11px] transition-all cursor-pointer inline-flex items-center gap-1.5"
                            title="Copy prompt for your AI assistant"
                          >
                            <span>⚔️ /interview</span>
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ) : (
        /* Markdown View */
        <div className="bg-black/40 border border-white/10 rounded-lg p-6 font-mono text-xs text-zinc-300 whitespace-pre-wrap leading-relaxed max-h-[500px] overflow-y-auto">
          {markdown || "No concept markdown log found."}
        </div>
      )}
    </div>
  );
}
