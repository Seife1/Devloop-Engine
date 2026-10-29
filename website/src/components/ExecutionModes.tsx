"use client";

import { useState } from "react";

type ModeFilter = "all" | "autonomous" | "interactive";

export default function ExecutionModes() {
  const [filter, setFilter] = useState<ModeFilter>("all");
  const [copiedPrompt, setCopiedPrompt] = useState<string | null>(null);

  const copyToClipboard = (text: string, label: string) => {
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(text);
      setCopiedPrompt(label);
      setTimeout(() => setCopiedPrompt(null), 2500);
    }
  };

  const matrixData = [
    {
      cluster: "track_intent",
      badge: "ACTIVE CODING",
      driver: "AI Default",
      driverType: "ai",
      when: "Before writing code, during design choices, and immediately after commits",
      needsAsk: "No (Automatic)",
      needsAskType: "no",
      action: "Declares files, logs trade-offs, reconciles git hashes",
    },
    {
      cluster: "manage_knowledge",
      badge: "KNOWLEDGE CATALOG",
      driver: "Split Hybrid",
      driverType: "split",
      when: "Auto-registers components; queries when developer asks for overview",
      needsAsk: "No for register / Yes for inspect",
      needsAskType: "split",
      action: "Living concept indexing & readiness scorecard",
    },
    {
      cluster: "manage_reviews",
      badge: "SPACED REPETITION",
      driver: "Developer",
      driverType: "user",
      when: "When running spaced reviews, daily active recall, or mock interviews",
      needsAsk: "Yes (Except 60s greeting)",
      needsAskType: "yes",
      action: "/review, /interview, SM-2 card rescheduling",
    },
    {
      cluster: "explore_project",
      badge: "ONBOARDING & DISCOVERY",
      driver: "Developer",
      driverType: "user",
      when: "When onboarding into a repo, requesting architecture tours, or setting goals",
      needsAsk: "Yes",
      needsAskType: "yes",
      action: "/tour, tech-stack detection, verified facts",
    },
  ];

  return (
    <section className="py-24 px-6 bg-[#F8FAFC] text-[#0B0F19] border-t border-zinc-200 relative overflow-hidden">
      {/* Background subtle radial glows */}
      <div className="absolute top-1/4 left-0 w-96 h-96 bg-emerald-500/5 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 right-0 w-96 h-96 bg-purple-500/5 rounded-full blur-3xl pointer-events-none" />

      {/* Copy notification toast */}
      {copiedPrompt && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 bg-emerald-600 text-white px-4 py-2 rounded-lg font-mono text-xs font-bold shadow-2xl flex items-center gap-2 animate-bounce">
          <span>✓</span>
          <span>Copied prompt: {copiedPrompt}! Paste into your IDE chat.</span>
        </div>
      )}

      <div className="max-w-7xl mx-auto relative z-10">
        {/* Section Header */}
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-14 gap-6">
          <div>
            <div className="flex items-center gap-2 mb-3">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-xs font-mono uppercase tracking-[0.2em] text-zinc-500 font-semibold">
                Dual-Mode Execution Architecture
              </span>
            </div>
            <h2 className="text-3xl sm:text-5xl font-serif text-zinc-900 tracking-tight">
              Autonomous pairing hygiene.{" "}
              <span className="italic font-normal text-zinc-500">
                Interactive mastery on demand.
              </span>
            </h2>
          </div>
          <p className="text-xs sm:text-sm text-zinc-600 max-w-md font-sans leading-relaxed">
            You never have to micromanage tools. LearnLoop operates on two synchronized gears:{" "}
            <strong className="text-zinc-900 font-semibold">80% runs quietly in the background</strong> without prompting, while{" "}
            <strong className="text-purple-700 font-semibold">interactive sparring</strong> activates only when you ask.
          </p>
        </div>

        {/* Interactive Filter Pills */}
        <div className="flex items-center gap-2 mb-10 overflow-x-auto pb-2 border-b border-zinc-200 text-xs font-mono">
          <span className="text-zinc-500 uppercase text-[10px] tracking-wider mr-2">Filter View:</span>
          <button
            onClick={() => setFilter("all")}
            className={`px-3 py-1.5 rounded transition-all cursor-pointer ${
              filter === "all"
                ? "bg-[#0B0F19] text-white font-medium shadow-sm"
                : "text-zinc-600 hover:text-black bg-white border border-zinc-200"
            }`}
          >
            All Workflows (Full Dual-Loop)
          </button>
          <button
            onClick={() => setFilter("autonomous")}
            className={`px-3 py-1.5 rounded transition-all cursor-pointer flex items-center gap-1.5 ${
              filter === "autonomous"
                ? "bg-emerald-50 text-emerald-800 font-bold border border-emerald-300 shadow-sm"
                : "text-zinc-600 hover:text-emerald-700 bg-white border border-zinc-200"
            }`}
          >
            <span>🤖 AI-Autonomous (80% Background)</span>
          </button>
          <button
            onClick={() => setFilter("interactive")}
            className={`px-3 py-1.5 rounded transition-all cursor-pointer flex items-center gap-1.5 ${
              filter === "interactive"
                ? "bg-purple-50 text-purple-800 font-bold border border-purple-300 shadow-sm"
                : "text-zinc-600 hover:text-purple-700 bg-white border border-zinc-200"
            }`}
          >
            <span>👤 Developer-Initiated (Interactive)</span>
          </button>
        </div>

        {/* Dual Cards Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-16">
          {/* Card 1: AI-Autonomous by Default */}
          {(filter === "all" || filter === "autonomous") && (
            <div className="bg-white border border-emerald-500/30 rounded-2xl p-7 sm:p-9 flex flex-col justify-between relative shadow-sm hover:shadow-md transition-all">
              <div className="absolute top-6 right-6">
                <span className="px-2.5 py-1 bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px] font-mono uppercase tracking-wider rounded-full font-medium">
                  Silent Background Hygiene
                </span>
              </div>

              <div>
                <div className="flex items-center gap-3 mb-4">
                  <span className="text-2xl p-2 bg-emerald-50 border border-emerald-200 rounded-lg">
                    🤖
                  </span>
                  <div>
                    <h3 className="text-xl sm:text-2xl font-serif text-zinc-900">
                      1. Used by AI by Default
                    </h3>
                    <div className="text-[11px] font-mono text-emerald-700 font-semibold">
                      AUTONOMOUS • RUNS QUIETLY • ~80% OF OPERATIONS
                    </div>
                  </div>
                </div>

                <p className="text-xs sm:text-sm text-zinc-600 font-sans leading-relaxed mb-6">
                  You never need to request these. Your AI assistant triggers them automatically as part of good pair-programming hygiene:
                </p>

                {/* Sub-items */}
                <div className="space-y-4">
                  <div className="bg-zinc-50 border border-zinc-200/80 rounded-xl p-4">
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="font-mono text-xs text-emerald-800 font-bold">
                        track_intent
                      </span>
                      <span className="text-[10px] font-mono text-zinc-500">
                        PRIMARY AI WORKHORSE
                      </span>
                    </div>
                    <ul className="text-xs text-zinc-600 font-sans space-y-2 mt-2 leading-relaxed">
                      <li className="flex items-start gap-2">
                        <code className="text-[11px] font-mono text-zinc-900 bg-white border border-zinc-200 px-1 rounded shrink-0">
                          action="start_session"
                        </code>
                        <span>
                          When you ask to build a feature, the AI declares target files and intent <strong>silently before editing</strong>.
                        </span>
                      </li>
                      <li className="flex items-start gap-2">
                        <code className="text-[11px] font-mono text-zinc-900 bg-white border border-zinc-200 px-1 rounded shrink-0">
                          action="log_decision"
                        </code>
                        <span>
                          When choosing between technical alternatives (e.g. SQLite vs JSON files), the AI preserves trade-offs automatically.
                        </span>
                      </li>
                      <li className="flex items-start gap-2">
                        <code className="text-[11px] font-mono text-zinc-900 bg-white border border-zinc-200 px-1 rounded shrink-0">
                          action="reconcile"
                        </code>
                        <span>
                          Immediately links your Git commit SHA with earlier declared intent upon git commit.
                        </span>
                      </li>
                    </ul>
                  </div>

                  <div className="bg-zinc-50 border border-zinc-200/80 rounded-xl p-4">
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="font-mono text-xs text-emerald-800 font-bold">
                        manage_knowledge (Passive)
                      </span>
                      <code className="text-[10px] font-mono text-zinc-500">action="register"</code>
                    </div>
                    <p className="text-xs text-zinc-600 font-sans leading-relaxed">
                      Whenever the AI builds a significant component or fixes an architectural bug, it registers it into your project catalog so it is ready for future defense.
                    </p>
                  </div>

                  <div className="bg-zinc-50 border border-zinc-200/80 rounded-xl p-4">
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="font-mono text-xs text-emerald-800 font-bold">
                        manage_reviews (Greeting)
                      </span>
                      <code className="text-[10px] font-mono text-zinc-500">action="briefing"</code>
                    </div>
                    <p className="text-xs text-zinc-600 font-sans leading-relaxed">
                      At session start, the AI runs this once to get a calm 60-second summary of recent code drift and due cards to greet you contextually.
                    </p>
                  </div>
                </div>
              </div>

              {/* Terminal Log Preview */}
              <div className="mt-6 pt-4 border-t border-zinc-200 font-mono text-[11px] text-zinc-500 flex items-center justify-between">
                <span>Developer experience:</span>
                <span className="text-emerald-700 font-semibold">✓ Uninterrupted coding flow</span>
              </div>
            </div>
          )}

          {/* Card 2: Developer-Initiated */}
          {(filter === "all" || filter === "interactive") && (
            <div className="bg-white border border-purple-500/30 rounded-2xl p-7 sm:p-9 flex flex-col justify-between relative shadow-sm hover:shadow-md transition-all">
              <div className="absolute top-6 right-6">
                <span className="px-2.5 py-1 bg-purple-50 text-purple-700 border border-purple-200 text-[10px] font-mono uppercase tracking-wider rounded-full font-medium">
                  On-Demand Mastery
                </span>
              </div>

              <div>
                <div className="flex items-center gap-3 mb-4">
                  <span className="text-2xl p-2 bg-purple-50 border border-purple-200 rounded-lg">
                    👤
                  </span>
                  <div>
                    <h3 className="text-xl sm:text-2xl font-serif text-zinc-900">
                      2. Prompted by You (Developer)
                    </h3>
                    <div className="text-[11px] font-mono text-purple-700 font-semibold">
                      INTERACTIVE • SOCRATIC SPARRING • ON-DEMAND LEARNING
                    </div>
                  </div>
                </div>

                <p className="text-xs sm:text-sm text-zinc-600 font-sans leading-relaxed mb-6">
                  These only happen when <strong>you</strong> explicitly request active recall, mock interview prep, or project exploration:
                </p>

                {/* Sub-items */}
                <div className="space-y-4">
                  <div className="bg-zinc-50 border border-zinc-200/80 rounded-xl p-4">
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="font-mono text-xs text-purple-800 font-bold">
                        manage_reviews (Interactive Spaced Review)
                      </span>
                      <span className="text-[10px] font-mono text-zinc-500">
                        Trigger: "Review due cards" or /review
                      </span>
                    </div>
                    <ul className="text-xs text-zinc-600 font-sans space-y-2 mt-2 leading-relaxed">
                      <li className="flex items-start gap-2">
                        <code className="text-[11px] font-mono text-zinc-900 bg-white border border-zinc-200 px-1 rounded shrink-0">
                          action="due"
                        </code>
                        <span>Pulls cards due today under SM-2 retention spacing.</span>
                      </li>
                      <li className="flex items-start gap-2">
                        <code className="text-[11px] font-mono text-zinc-900 bg-white border border-zinc-200 px-1 rounded shrink-0">
                          action="record"
                        </code>
                        <span>
                          The AI grades your typed explanation against the ground-truth rubric and reschedules the interval.
                        </span>
                      </li>
                      <li className="flex items-start gap-2">
                        <code className="text-[11px] font-mono text-zinc-900 bg-white border border-zinc-200 px-1 rounded shrink-0">
                          action="snooze"
                        </code>
                        <span>Temporarily pauses cards when you say <em>"Snooze this for next week"</em>.</span>
                      </li>
                    </ul>
                  </div>

                  <div className="bg-zinc-50 border border-zinc-200/80 rounded-xl p-4">
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="font-mono text-xs text-purple-800 font-bold">
                        explore_project (Codebase Tour & Lore)
                      </span>
                      <span className="text-[10px] font-mono text-zinc-500">
                        Trigger: "Tour the codebase" or /tour
                      </span>
                    </div>
                    <ul className="text-xs text-zinc-600 font-sans space-y-2 mt-2 leading-relaxed">
                      <li className="flex items-start gap-2">
                        <code className="text-[11px] font-mono text-zinc-900 bg-white border border-zinc-200 px-1 rounded shrink-0">
                          action="tour"
                        </code>
                        <span>
                          Organizes the repo into cognitive bands (Basic &rarr; Intermediate &rarr; Advanced) with checkpoint questions.
                        </span>
                      </li>
                      <li className="flex items-start gap-2">
                        <code className="text-[11px] font-mono text-zinc-900 bg-white border border-zinc-200 px-1 rounded shrink-0">
                          action="add_fact"
                        </code>
                        <span>Uncovers verified computing history, spec upgrades, or architecture lore.</span>
                      </li>
                    </ul>
                  </div>

                  <div className="bg-zinc-50 border border-zinc-200/80 rounded-xl p-4">
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="font-mono text-xs text-purple-800 font-bold">
                        manage_knowledge (Inspection)
                      </span>
                      <code className="text-[10px] font-mono text-zinc-500">action="list" | "readiness"</code>
                    </div>
                    <p className="text-xs text-zinc-600 font-sans leading-relaxed">
                      Triggered when you ask <em>"What concepts have we documented?"</em> or <em>"Show project readiness"</em> to inspect explained vs shaky invariants.
                    </p>
                  </div>
                </div>
              </div>

              {/* Click-to-copy quick prompts */}
              <div className="mt-6 pt-4 border-t border-zinc-200">
                <span className="block text-[10px] font-mono uppercase tracking-wider text-zinc-500 mb-2">
                  Try typing these in your editor chat:
                </span>
                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={() => copyToClipboard("/review", "/review")}
                    className="px-2.5 py-1 bg-zinc-100 hover:bg-purple-600 hover:text-white border border-zinc-200 rounded font-mono text-[11px] text-purple-800 transition-colors cursor-pointer font-medium"
                  >
                    /review 📋
                  </button>
                  <button
                    onClick={() => copyToClipboard("/interview", "/interview")}
                    className="px-2.5 py-1 bg-zinc-100 hover:bg-purple-600 hover:text-white border border-zinc-200 rounded font-mono text-[11px] text-purple-800 transition-colors cursor-pointer font-medium"
                  >
                    /interview 📋
                  </button>
                  <button
                    onClick={() => copyToClipboard("/tour", "/tour")}
                    className="px-2.5 py-1 bg-zinc-100 hover:bg-purple-600 hover:text-white border border-zinc-200 rounded font-mono text-[11px] text-purple-800 transition-colors cursor-pointer font-medium"
                  >
                    /tour 📋
                  </button>
                  <button
                    onClick={() => copyToClipboard("Catch me up on changes", "catch-up")}
                    className="px-2.5 py-1 bg-zinc-100 hover:bg-purple-600 hover:text-white border border-zinc-200 rounded font-mono text-[11px] text-zinc-800 transition-colors cursor-pointer font-medium"
                  >
                    "Catch me up" 📋
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Quick Summary Matrix */}
        <div className="bg-white border border-zinc-200 rounded-2xl p-6 sm:p-8 shadow-sm">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6 pb-4 border-b border-zinc-200">
            <div>
              <div className="text-[10px] font-mono tracking-widest uppercase text-zinc-500 mb-1 font-semibold">
                Execution Reference
              </div>
              <h3 className="text-xl font-serif text-zinc-900">
                Cluster Summary Matrix
              </h3>
            </div>
            <div className="text-xs font-mono text-zinc-500">
              4 Clustered Domains • 100% Deterministic SQLite
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono border-collapse">
              <thead>
                <tr className="border-b border-zinc-200 text-zinc-500 text-[11px] uppercase tracking-wider">
                  <th className="py-3 px-4">Cluster</th>
                  <th className="py-3 px-4">Primary Driver</th>
                  <th className="py-3 px-4">When It Fires</th>
                  <th className="py-3 px-4">Does User Need to Ask?</th>
                  <th className="py-3 px-4">Primary Role</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100">
                {matrixData.map((row) => (
                  <tr key={row.cluster} className="hover:bg-zinc-50 transition-colors">
                    <td className="py-4 px-4">
                      <div className="font-bold text-zinc-900 text-sm">{row.cluster}</div>
                      <div className="text-[10px] text-zinc-500 uppercase">{row.badge}</div>
                    </td>
                    <td className="py-4 px-4 whitespace-nowrap">
                      {row.driverType === "ai" && (
                        <span className="px-2.5 py-1 bg-emerald-50 text-emerald-800 border border-emerald-200 rounded-md font-semibold inline-flex items-center gap-1.5">
                          <span>🤖</span>
                          <span>AI Default</span>
                        </span>
                      )}
                      {row.driverType === "user" && (
                        <span className="px-2.5 py-1 bg-purple-50 text-purple-800 border border-purple-200 rounded-md font-semibold inline-flex items-center gap-1.5">
                          <span>👤</span>
                          <span>Developer</span>
                        </span>
                      )}
                      {row.driverType === "split" && (
                        <span className="px-2.5 py-1 bg-blue-50 text-blue-800 border border-blue-200 rounded-md font-semibold inline-flex items-center gap-1.5">
                          <span>🔄</span>
                          <span>Split Hybrid</span>
                        </span>
                      )}
                    </td>
                    <td className="py-4 px-4 text-zinc-600 font-sans text-xs max-w-xs leading-relaxed">
                      {row.when}
                    </td>
                    <td className="py-4 px-4 whitespace-nowrap">
                      {row.needsAskType === "no" && (
                        <span className="text-emerald-700 font-bold flex items-center gap-1">
                          <span>✕</span>
                          <span>No (Automatic)</span>
                        </span>
                      )}
                      {row.needsAskType === "yes" && (
                        <span className="text-purple-700 font-bold flex items-center gap-1">
                          <span>✓</span>
                          <span>Yes (On-demand)</span>
                        </span>
                      )}
                      {row.needsAskType === "split" && (
                        <span className="text-blue-700 font-semibold">
                          No for register / Yes for inspect
                        </span>
                      )}
                    </td>
                    <td className="py-4 px-4 text-zinc-700 font-sans text-xs max-w-xs leading-relaxed">
                      {row.action}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>
  );
}
