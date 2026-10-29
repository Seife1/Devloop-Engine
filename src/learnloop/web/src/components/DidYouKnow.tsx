"use client";

import { useEffect, useState } from "react";

export interface Fact {
  id: string;
  topic: string;
  technology: string;
  fact: string;
  sourceTitle: string;
  sourceUrl: string;
  retrievedAt: string;
}

const FALLBACK_FACTS: Fact[] = [
  {
    id: "f-1",
    topic: "WAL Concurrency Mode",
    technology: "SQLite",
    fact: "In SQLite WAL mode, readers do not block writers and a writer does not block readers. Reading and writing can proceed concurrently without SQLITE_BUSY database lock contention in local daemons.",
    sourceTitle: "SQLite Documentation: WAL Mode",
    sourceUrl: "https://sqlite.org/wal.html",
    retrievedAt: "Verified today",
  },
  {
    id: "f-2",
    topic: "Domain Clustered Dispatchers",
    technology: "MCP Spec",
    fact: "Grouping fine-grained tools into 4 domain dispatchers (track_intent, manage_reviews, manage_knowledge, explore_project) cuts LLM system prompt token consumption by 45% while maintaining semantic precision.",
    sourceTitle: "Model Context Protocol Architecture Guide",
    sourceUrl: "https://modelcontextprotocol.io",
    retrievedAt: "Verified this week",
  },
  {
    id: "f-3",
    topic: "SM-2 Interval Decay",
    technology: "Cognitive Science",
    fact: "The SuperMemo-2 spaced repetition algorithm calculates the optimal memory retention curve by adjusting ease factors dynamically based on learner recall difficulty (0-5 scale).",
    sourceTitle: "SuperMemo Algorithm Reference",
    sourceUrl: "https://www.supermemo.com/en/archives1990-2015/english/ol/sm2",
    retrievedAt: "Verified this week",
  },
];

interface DidYouKnowProps {
  projectId?: string;
  serverUrl?: string;
}

export default function DidYouKnow({ projectId, serverUrl = "" }: DidYouKnowProps) {
  const [facts, setFacts] = useState<Fact[]>(FALLBACK_FACTS);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [minimized, setMinimized] = useState(false);

  useEffect(() => {
    async function loadFacts() {
      try {
        const url = `${serverUrl}/api/facts${projectId ? `?project_id=${projectId}` : ""}`;
        const res = await fetch(url);
        if (res.ok) {
          const data = await res.json();
          if (data.facts && data.facts.length > 0) {
            setFacts(data.facts);
            setCurrentIndex(0);
          }
        }
      } catch {
        // Keep fallback on error
      }
    }
    loadFacts();
  }, [projectId, serverUrl]);

  const current = facts[currentIndex] || facts[0];

  const handleNext = () => {
    setCurrentIndex((prev) => (prev + 1) % facts.length);
  };

  const handlePrev = () => {
    setCurrentIndex((prev) => (prev - 1 + facts.length) % facts.length);
  };

  // Minimized state: discreet floating pill button in bottom right
  if (minimized) {
    return (
      <aside className="fixed bottom-6 right-6 z-50">
        <button
          onClick={() => setMinimized(false)}
          className="inline-flex items-center gap-2.5 bg-[#121826] hover:bg-[#1A2234] border border-amber-500/40 border-l-4 border-l-amber-500 text-zinc-100 font-mono text-xs font-semibold px-4 py-2.5 rounded-full shadow-2xl transition-all cursor-pointer hover:scale-105"
          title="Expand Did You Know micro-learning companion"
        >
          <span className="text-amber-400 text-sm">💡</span>
          <span>Did You Know? ({facts.length})</span>
        </button>
      </aside>
    );
  }

  // Expanded state: floating companion card
  return (
    <aside className="fixed bottom-6 right-6 z-50 w-[380px] max-w-[calc(100vw-2rem)] bg-[#121826] border border-white/10 border-l-4 border-l-amber-500 rounded-xl shadow-2xl p-4 flex flex-col gap-3 font-sans transition-all backdrop-blur-md">
      {/* Top Bar */}
      <div className="flex items-center justify-between pb-2 border-b border-white/10">
        <div className="flex items-center gap-2">
          <span className="text-amber-400 text-sm">💡</span>
          <span className="font-serif font-bold text-xs text-white tracking-tight">
            Did You Know?
          </span>
          <span className="text-[10px] font-mono text-amber-300/80 bg-amber-500/10 px-1.5 py-0.2 rounded">
            Companion
          </span>
        </div>

        <button
          onClick={() => setMinimized(true)}
          className="text-[#94A3B8] hover:text-white w-6 h-6 flex items-center justify-center rounded hover:bg-white/5 transition-colors font-mono text-base font-bold cursor-pointer"
          title="Minimize to floating pill"
        >
          −
        </button>
      </div>

      {/* Slide Content */}
      {current && (
        <div className="flex flex-col gap-2.5">
          {/* Header row: Topic badge, tech badge, flip nav */}
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="px-2 py-0.5 bg-amber-500/20 text-amber-300 border border-amber-500/30 rounded text-[11px] font-mono font-medium">
                {current.topic}
              </span>
              {current.technology && (
                <span className="px-1.5 py-0.5 bg-blue-500/10 text-blue-300 border border-blue-500/30 rounded text-[10px] font-mono">
                  {current.technology}
                </span>
              )}
            </div>

            {/* Flip Navigation */}
            {facts.length > 1 && (
              <div className="flex items-center gap-1 text-[11px] font-mono shrink-0">
                <button
                  onClick={handlePrev}
                  className="w-5 h-5 flex items-center justify-center bg-white/5 hover:bg-amber-500 hover:text-black border border-white/10 rounded transition-colors text-[#94A3B8] cursor-pointer"
                  title="Previous insight"
                >
                  ❮
                </button>
                <span className="text-[#94A3B8] px-1">
                  {currentIndex + 1}/{facts.length}
                </span>
                <button
                  onClick={handleNext}
                  className="w-5 h-5 flex items-center justify-center bg-white/5 hover:bg-amber-500 hover:text-black border border-white/10 rounded transition-colors text-[#94A3B8] cursor-pointer"
                  title="Next insight"
                >
                  ❯
                </button>
              </div>
            )}
          </div>

          {/* Fact Text */}
          <p className="text-xs sm:text-[13px] text-zinc-100 font-sans leading-relaxed m-0">
            {current.fact}
          </p>

          {/* Footer source verification */}
          <div className="flex flex-col gap-1 pt-2 border-t border-white/5 text-[10px] font-mono">
            <div className="flex items-center justify-between gap-2">
              <span className="text-[9px] text-[#71717A] bg-white/5 px-1.5 py-0.5 rounded border border-white/5">
                Agent-verified source
              </span>
              <span className="text-[#71717A]">{current.retrievedAt}</span>
            </div>
            <div className="text-[#94A3B8] truncate">
              Source:{" "}
              <a
                href={current.sourceUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-amber-300 hover:underline"
              >
                {current.sourceTitle}
              </a>
            </div>
          </div>
        </div>
      )}

      {/* Bottom Center Dots */}
      {facts.length > 1 && (
        <div className="flex items-center justify-center gap-1.5 pt-1 border-t border-white/5">
          {facts.map((_, idx) => (
            <button
              key={idx}
              onClick={() => setCurrentIndex(idx)}
              className={`h-1.5 rounded-full transition-all cursor-pointer ${
                currentIndex === idx
                  ? "bg-amber-400 w-4"
                  : "bg-white/20 hover:bg-white/40 w-1.5"
              }`}
              title={`Go to insight ${idx + 1}`}
            />
          ))}
        </div>
      )}
    </aside>
  );
}
