"use client";

import { useEffect, useState } from "react";

interface OverviewData {
  project: {
    id: string;
    name: string;
    repo_path: string;
    folder: string;
    created_at: string;
  };
  readiness: {
    headline: string;
    score: number;
    stale_count: number;
    due_count: number;
    total_items: number;
    status_counts?: Record<string, number>;
  };
  technologies: Array<{
    name: string;
    ecosystem: string;
    version_spec?: string;
    source_file?: string;
  }>;
  tags: string[];
  commits: Array<{
    sha: string;
    message: string;
    committed_at: string;
    files: string[];
  }>;
  queue_waiting: number;
  description: string;
}

interface OverviewTabProps {
  projectId: string;
  serverUrl?: string;
  onNavigateToReviews: () => void;
  onNavigateToConcepts: () => void;
}

export default function OverviewTab({
  projectId,
  serverUrl = "",
  onNavigateToReviews,
  onNavigateToConcepts,
}: OverviewTabProps) {
  const [data, setData] = useState<OverviewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    async function fetchOverview() {
      if (!projectId) return;
      setLoading(true);
      try {
        const res = await fetch(`${serverUrl}/api/projects/${projectId}/overview`);
        if (res.ok) {
          const json = await res.json();
          setData(json);
        }
      } catch (err) {
        console.error("Failed to load project overview:", err);
      } finally {
        setLoading(false);
      }
    }
    fetchOverview();
  }, [projectId, serverUrl]);

  const copyPrompt = (prompt: string, feedback: string) => {
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(prompt);
      setToast(feedback);
      setTimeout(() => setToast(null), 3000);
    }
  };

  if (loading || !data) {
    return (
      <div className="py-12 text-center text-xs font-mono text-[#94A3B8]">
        Loading live project telemetry from SQLite and Git...
      </div>
    );
  }

  const { project, readiness, technologies, tags, commits, queue_waiting, description } = data;

  return (
    <div className="flex flex-col gap-8 relative">
      {/* Toast Notification */}
      {toast && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 bg-emerald-500 text-black px-4 py-2 rounded-lg font-mono text-xs font-bold shadow-2xl flex items-center gap-2 animate-bounce">
          <span>✓</span>
          <span>{toast}</span>
        </div>
      )}

      {/* Project Hero Header */}
      <div className="bg-[#121826] border border-white/10 rounded-xl p-6 sm:p-8 flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <div className="flex items-center gap-2 mb-2 font-mono text-xs">
            <span className="px-2 py-0.5 bg-blue-500/20 text-blue-300 border border-blue-500/30 rounded font-semibold">
              Project ID: {project.id}
            </span>
            <span className="text-[#94A3B8]">Folder:</span>
            <code className="text-zinc-300 bg-white/5 px-2 py-0.5 rounded">
              {project.folder}
            </code>
          </div>
          <h1 className="text-2xl sm:text-3xl font-serif text-white tracking-tight mb-2">
            {project.name}
          </h1>
          <p className="text-xs sm:text-sm text-[#94A3B8] font-sans max-w-2xl leading-relaxed">
            {description || readiness.headline}
          </p>

          {tags.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-4">
              {tags.map((t, idx) => (
                <span
                  key={idx}
                  className="px-2 py-0.5 bg-white/5 border border-white/10 rounded text-[11px] font-mono text-zinc-300"
                >
                  🏷️ {t}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Action Button */}
        <div className="flex flex-row md:flex-col gap-3 shrink-0">
          <button
            onClick={onNavigateToReviews}
            className="px-4 py-2.5 bg-emerald-500 hover:bg-emerald-400 text-black font-mono font-bold text-xs uppercase tracking-wider rounded-lg transition-all cursor-pointer flex items-center justify-center gap-2 shadow-lg hover:shadow-emerald-500/20"
          >
            <span>Active Recall Quiz ({readiness.due_count})</span>
            <span>→</span>
          </button>
          <button
            onClick={onNavigateToConcepts}
            className="px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 text-white font-mono text-xs rounded-lg transition-colors cursor-pointer text-center"
          >
            Browse Concept Log
          </button>
        </div>
      </div>

      {/* Metrics Bento Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric 1: Readiness Score */}
        <div className="bg-[#121826] border border-white/10 rounded-xl p-5">
          <div className="text-[10px] font-mono uppercase tracking-wider text-[#94A3B8] mb-1">
            Readiness Score
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-mono font-bold text-white">
              {readiness.score}
            </span>
            <span className="text-xs font-mono text-[#71717A]">/ 100</span>
          </div>
          <div className="text-[11px] text-[#94A3B8] font-sans mt-2 truncate">
            {readiness.headline}
          </div>
        </div>

        {/* Metric 2: Reviews Due */}
        <div
          onClick={readiness.due_count > 0 ? onNavigateToReviews : undefined}
          className={`bg-[#121826] border border-white/10 rounded-xl p-5 transition-all ${
            readiness.due_count > 0 ? "hover:border-amber-500/50 cursor-pointer" : ""
          }`}
        >
          <div className="flex items-center justify-between mb-1">
            <span className="text-[10px] font-mono uppercase tracking-wider text-[#94A3B8]">
              Spaced Reviews Due
            </span>
            {readiness.due_count > 0 && (
              <span className="text-[9px] font-mono text-amber-300 bg-amber-500/10 px-1.5 py-0.5 rounded border border-amber-500/20">
                Due Today
              </span>
            )}
          </div>
          <div className="text-3xl font-mono font-bold text-amber-300">
            {readiness.due_count}
          </div>
          <div className="text-[11px] text-[#94A3B8] font-sans mt-2 flex items-center justify-between">
            <span>Ready for active recall</span>
            {readiness.due_count > 0 && (
              <span className="text-amber-300 font-mono text-[10px] underline">
                Start &rarr;
              </span>
            )}
          </div>
        </div>

        {/* Metric 3: Stale Invariants */}
        <div
          onClick={readiness.stale_count > 0 ? onNavigateToConcepts : undefined}
          className={`bg-[#121826] border border-white/10 rounded-xl p-5 transition-all ${
            readiness.stale_count > 0 ? "hover:border-rose-500/50 cursor-pointer" : ""
          }`}
        >
          <div className="flex items-center justify-between mb-1">
            <span className="text-[10px] font-mono uppercase tracking-wider text-[#94A3B8]">
              Stale Invariants
            </span>
            {readiness.stale_count > 0 && (
              <span className="text-[9px] font-mono text-rose-300 bg-rose-500/10 px-1.5 py-0.5 rounded border border-rose-500/20">
                Code Drifted
              </span>
            )}
          </div>
          <div className="text-3xl font-mono font-bold text-rose-400">
            {readiness.stale_count}
          </div>
          <div className="text-[11px] text-[#94A3B8] font-sans mt-2 flex items-center justify-between">
            <span>Modified by recent commits</span>
            {readiness.stale_count > 0 && (
              <span className="text-rose-300 font-mono text-[10px] underline">
                View &rarr;
              </span>
            )}
          </div>
        </div>

        {/* Metric 4: Git Queue */}
        <div className="bg-[#121826] border border-white/10 rounded-xl p-5">
          <div className="text-[10px] font-mono uppercase tracking-wider text-[#94A3B8] mb-1">
            Unexplained Commits
          </div>
          <div className="text-3xl font-mono font-bold text-blue-400">
            {queue_waiting}
          </div>
          <div className="text-[11px] text-[#94A3B8] font-sans mt-2">
            {queue_waiting === 0 ? "✓ Git queue synchronized" : "Waiting in .learn/queue"}
          </div>
        </div>
      </div>

      {/* Interactive AI Sparring Banner */}
      <div className="bg-gradient-to-r from-blue-900/25 via-purple-900/20 to-black/30 border border-blue-500/20 rounded-xl p-6 flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="flex items-start gap-4">
          <span className="text-2xl p-2.5 bg-blue-500/10 border border-blue-500/20 rounded-lg shrink-0">
            ⚔️
          </span>
          <div>
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <span className="font-serif font-bold text-base text-white">
                The Real Learning Happens in Your IDE
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 bg-blue-500/20 text-blue-300 border border-blue-500/30 rounded">
                Direct AI Feedback
              </span>
            </div>
            <p className="text-xs text-[#94A3B8] font-sans leading-relaxed max-w-2xl">
              This dashboard acts as your mission control, tracking your retention curve and drift. But inside{" "}
              <strong className="text-zinc-200">Cursor, Windsurf, or VS Code</strong>, your AI assistant analyzes your actual code diffs, challenges your implementation assumptions, and gives you instant verbal defense practice.
            </p>
          </div>
        </div>
        <div className="flex flex-col sm:flex-row md:flex-col gap-2 shrink-0">
          <button
            onClick={() =>
              copyPrompt(
                "/interview on recent changes and architecture",
                "Copied '/interview' prompt! Paste into your IDE chat."
              )
            }
            className="px-4 py-2.5 bg-purple-600 hover:bg-purple-500 text-white font-mono text-xs font-semibold rounded-lg transition-colors cursor-pointer flex items-center justify-center gap-2 shadow-lg hover:shadow-purple-500/20"
          >
            <span>Spar: /interview</span>
            <span>📋</span>
          </button>
          <button
            onClick={() =>
              copyPrompt(
                "/review",
                "Copied '/review' prompt! Paste into your IDE chat."
              )
            }
            className="px-4 py-2 bg-white/10 hover:bg-white/20 border border-white/15 text-white font-mono text-xs rounded-lg transition-colors cursor-pointer flex items-center justify-center gap-2"
          >
            <span>Review: /review</span>
            <span>📋</span>
          </button>
        </div>
      </div>

      {/* Two Column Layout: Technologies & Commits */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Technologies Grid */}
        <div className="bg-[#121826] border border-white/10 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4 pb-3 border-b border-white/10">
            <h3 className="font-serif text-lg text-white">
              🛠️ Detected Technologies ({technologies.length})
            </h3>
            <span className="text-[10px] font-mono text-[#94A3B8] uppercase">
              Auto-scanned
            </span>
          </div>

          {technologies.length === 0 ? (
            <div className="py-6 text-center text-xs font-mono text-[#71717A]">
              No technologies cataloged yet.
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-2.5 max-h-72 overflow-y-auto">
              {technologies.map((t, idx) => (
                <div
                  key={idx}
                  className="p-2.5 bg-black/40 border border-white/5 rounded-lg text-xs font-mono"
                >
                  <div className="font-semibold text-white truncate">
                    {t.name}
                  </div>
                  <div className="flex items-center justify-between text-[10px] text-[#71717A] mt-1">
                    <span className="uppercase">{t.ecosystem}</span>
                    <span>{t.version_spec || ""}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Verified Commits */}
        <div className="bg-[#121826] border border-white/10 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4 pb-3 border-b border-white/10">
            <h3 className="font-serif text-lg text-white">
              📦 Verified Git Commits
            </h3>
            <span className="text-[10px] font-mono text-emerald-300">
              Proof of Outcome
            </span>
          </div>

          {commits.length === 0 ? (
            <div className="py-6 text-center text-xs font-mono text-[#71717A]">
              No commits recorded yet.
            </div>
          ) : (
            <div className="flex flex-col divide-y divide-white/5 max-h-72 overflow-y-auto">
              {commits.map((c) => (
                <div
                  key={c.sha}
                  className="py-2.5 text-xs font-mono flex flex-col gap-1"
                >
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="text-blue-400 font-bold">{c.sha}</span>
                    <span className="text-[#71717A]">{c.committed_at}</span>
                  </div>
                  <div className="font-sans text-zinc-200 text-xs truncate">
                    {c.message}
                  </div>
                  {c.files && c.files.length > 0 && (
                    <div className="text-[10px] text-[#71717A] truncate">
                      {c.files.length} files modified
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
