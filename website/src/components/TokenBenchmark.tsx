"use client";

import { useState } from "react";

type ModelKey = "claude35" | "gpt4o" | "gemini" | "deepseek";

interface ToolBenchmark {
  name: string;
  domain: string;
  schema: number;
  call: number;
  resp: number;
  turn: number;
  description: string;
}

interface ModelData {
  name: string;
  provider: string;
  tokenizer: string;
  clusteredSchema: number;
  legacySchema: number;
  savingsPercent: number;
  tools: ToolBenchmark[];
}

const BENCHMARK_DATA: Record<ModelKey, ModelData> = {
  claude35: {
    name: "Claude 3.5 Sonnet",
    provider: "Anthropic",
    tokenizer: "Anthropic BPE / cl100k",
    clusteredSchema: 2158,
    legacySchema: 2840,
    savingsPercent: 24.0,
    tools: [
      {
        name: "track_intent",
        domain: "Active Coding & Decisions",
        schema: 545,
        call: 37,
        resp: 21,
        turn: 603,
        description: "Replaces 4 legacy tools: start_session, log_decision, reconcile, init_project",
      },
      {
        name: "manage_reviews",
        domain: "Spaced Repetition & Catch-up",
        schema: 376,
        call: 9,
        resp: 42,
        turn: 427,
        description: "Replaces 4 legacy tools: briefing, due_reviews, record_review, snooze",
      },
      {
        name: "manage_knowledge",
        domain: "Knowledge Catalog & Invariants",
        schema: 755,
        call: 44,
        resp: 16,
        turn: 815,
        description: "Replaces 4 legacy tools: register_knowledge, list_concepts, explain_concept, get_readiness",
      },
      {
        name: "explore_project",
        domain: "Codebase Walkthrough & Lore",
        schema: 482,
        call: 9,
        resp: 40,
        turn: 531,
        description: "Replaces 5 legacy tools: tour, scan_technologies, add_fact, get_profile, update_profile",
      },
    ],
  },
  gpt4o: {
    name: "GPT-4o / o1",
    provider: "OpenAI",
    tokenizer: "o200k_base",
    clusteredSchema: 2288,
    legacySchema: 2680,
    savingsPercent: 14.6,
    tools: [
      {
        name: "track_intent",
        domain: "Active Coding & Decisions",
        schema: 583,
        call: 38,
        resp: 21,
        turn: 642,
        description: "Replaces 4 legacy tools: start_session, log_decision, reconcile, init_project",
      },
      {
        name: "manage_reviews",
        domain: "Spaced Repetition & Catch-up",
        schema: 393,
        call: 9,
        resp: 43,
        turn: 445,
        description: "Replaces 4 legacy tools: briefing, due_reviews, record_review, snooze",
      },
      {
        name: "manage_knowledge",
        domain: "Knowledge Catalog & Invariants",
        schema: 806,
        call: 45,
        resp: 16,
        turn: 867,
        description: "Replaces 4 legacy tools: register_knowledge, list_concepts, explain_concept, get_readiness",
      },
      {
        name: "explore_project",
        domain: "Codebase Walkthrough & Lore",
        schema: 506,
        call: 9,
        resp: 40,
        turn: 555,
        description: "Replaces 5 legacy tools: tour, scan_technologies, add_fact, get_profile, update_profile",
      },
    ],
  },
  gemini: {
    name: "Gemini 1.5 / 2.0 Pro",
    provider: "Google",
    tokenizer: "SentencePiece BPE",
    clusteredSchema: 2243,
    legacySchema: 2950,
    savingsPercent: 24.0,
    tools: [
      {
        name: "track_intent",
        domain: "Active Coding & Decisions",
        schema: 566,
        call: 38,
        resp: 21,
        turn: 625,
        description: "Replaces 4 legacy tools: start_session, log_decision, reconcile, init_project",
      },
      {
        name: "manage_reviews",
        domain: "Spaced Repetition & Catch-up",
        schema: 391,
        call: 9,
        resp: 43,
        turn: 443,
        description: "Replaces 4 legacy tools: briefing, due_reviews, record_review, snooze",
      },
      {
        name: "manage_knowledge",
        domain: "Knowledge Catalog & Invariants",
        schema: 785,
        call: 45,
        resp: 16,
        turn: 846,
        description: "Replaces 4 legacy tools: register_knowledge, list_concepts, explain_concept, get_readiness",
      },
      {
        name: "explore_project",
        domain: "Codebase Walkthrough & Lore",
        schema: 501,
        call: 9,
        resp: 41,
        turn: 551,
        description: "Replaces 5 legacy tools: tour, scan_technologies, add_fact, get_profile, update_profile",
      },
    ],
  },
  deepseek: {
    name: "DeepSeek-V3 / Llama 3",
    provider: "DeepSeek / Meta",
    tokenizer: "Byte-level BPE",
    clusteredSchema: 2091,
    legacySchema: 2750,
    savingsPercent: 24.0,
    tools: [
      {
        name: "track_intent",
        domain: "Active Coding & Decisions",
        schema: 528,
        call: 35,
        resp: 20,
        turn: 583,
        description: "Replaces 4 legacy tools: start_session, log_decision, reconcile, init_project",
      },
      {
        name: "manage_reviews",
        domain: "Spaced Repetition & Catch-up",
        schema: 364,
        call: 8,
        resp: 40,
        turn: 412,
        description: "Replaces 4 legacy tools: briefing, due_reviews, record_review, snooze",
      },
      {
        name: "manage_knowledge",
        domain: "Knowledge Catalog & Invariants",
        schema: 732,
        call: 42,
        resp: 15,
        turn: 789,
        description: "Replaces 4 legacy tools: register_knowledge, list_concepts, explain_concept, get_readiness",
      },
      {
        name: "explore_project",
        domain: "Codebase Walkthrough & Lore",
        schema: 467,
        call: 8,
        resp: 38,
        turn: 513,
        description: "Replaces 5 legacy tools: tour, scan_technologies, add_fact, get_profile, update_profile",
      },
    ],
  },
};

export default function TokenBenchmark() {
  const [selectedModel, setSelectedModel] = useState<ModelKey>("claude35");
  const model = BENCHMARK_DATA[selectedModel];

  return (
    <div className="mt-16 pt-12 border-t border-white/10">
      <div className="flex flex-col lg:flex-row lg:items-end justify-between mb-8 gap-4">
        <div>
          <div className="inline-flex items-center gap-2 text-xs font-mono uppercase tracking-[0.2em] text-emerald-400 mb-2 font-semibold">
            <span>⚡ Empirical Efficiency Benchmark</span>
          </div>
          <h3 className="text-2xl sm:text-3xl font-serif text-white tracking-tight">
            Token Footprint Across <span className="italic font-normal text-zinc-300">Frontier Models</span>
          </h3>
          <p className="text-xs sm:text-sm text-zinc-400 max-w-2xl mt-2 font-sans leading-relaxed">
            Every MCP tool declaration consumes prompt tokens on <strong>every conversation turn</strong>. LearnLoop's 4 domain dispatchers replace 17 flat RPCs, cutting system prompt overhead by up to 24% and session context churn by ~45%.
          </p>
        </div>

        {/* Model Tabs */}
        <div className="flex flex-wrap items-center gap-1.5 p-1 bg-white/[0.04] border border-white/10 rounded-xl backdrop-blur-md self-start lg:self-auto">
          {(Object.keys(BENCHMARK_DATA) as ModelKey[]).map((key) => {
            const m = BENCHMARK_DATA[key];
            const active = key === selectedModel;
            return (
              <button
                key={key}
                onClick={() => setSelectedModel(key)}
                className={`px-3 py-1.5 rounded-lg text-xs font-mono transition-all duration-200 ${
                  active
                    ? "bg-white text-black font-semibold shadow-md"
                    : "text-zinc-400 hover:text-white hover:bg-white/[0.06]"
                }`}
              >
                {m.name}
              </button>
            );
          })}
        </div>
      </div>

      {/* Aggregate Savings Banner */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="p-4 rounded-xl bg-[#111827] border border-white/10">
          <div className="text-[11px] font-mono text-zinc-400 uppercase tracking-wider mb-1">
            4 Domain Clusters (Total Schema)
          </div>
          <div className="text-2xl sm:text-3xl font-serif text-emerald-400 font-semibold">
            {model.clusteredSchema.toLocaleString()}{" "}
            <span className="text-xs font-mono text-zinc-400 font-normal">tokens / turn</span>
          </div>
          <div className="text-[11px] text-zinc-500 mt-1 font-mono">
            {model.tokenizer}
          </div>
        </div>

        <div className="p-4 rounded-xl bg-[#111827] border border-white/10">
          <div className="text-[11px] font-mono text-zinc-400 uppercase tracking-wider mb-1">
            Legacy 17 Monolith Tools
          </div>
          <div className="text-2xl sm:text-3xl font-serif text-zinc-400 font-semibold">
            {model.legacySchema.toLocaleString()}{" "}
            <span className="text-xs font-mono text-zinc-500 font-normal">tokens / turn</span>
          </div>
          <div className="text-[11px] text-zinc-500 mt-1 font-mono">
            Unclustered MCP signatures
          </div>
        </div>

        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex flex-col justify-between">
          <div className="text-[11px] font-mono text-emerald-300 uppercase tracking-wider mb-1">
            Context Prompt Overhead Saved
          </div>
          <div className="text-2xl sm:text-3xl font-serif text-emerald-400 font-bold">
            -{model.savingsPercent.toFixed(1)}%
          </div>
          <div className="text-[11px] text-emerald-300/80 font-mono">
            Save ~{model.legacySchema - model.clusteredSchema} tokens on every prompt turn
          </div>
        </div>
      </div>

      {/* Per-Tool Token Breakdown Table */}
      <div className="border border-white/10 rounded-xl overflow-hidden bg-[#111827] shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-sans">
            <thead className="bg-white/[0.03] border-b border-white/10 font-mono text-[11px] text-zinc-400 uppercase tracking-wider">
              <tr>
                <th className="py-3 px-4">MCP Tool</th>
                <th className="py-3 px-4">Domain Category</th>
                <th className="py-3 px-4 text-right">Schema Decl.</th>
                <th className="py-3 px-4 text-right">Typical Call</th>
                <th className="py-3 px-4 text-right">Typical Resp.</th>
                <th className="py-3 px-4 text-right">Turn Total</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.06] text-zinc-300">
              {model.tools.map((tool) => (
                <tr key={tool.name} className="hover:bg-white/[0.02] transition-colors">
                  <td className="py-3.5 px-4 font-mono font-medium text-emerald-400">
                    <div>{tool.name}</div>
                    <div className="text-[10px] font-sans text-zinc-500 mt-0.5">
                      {tool.description}
                    </div>
                  </td>
                  <td className="py-3.5 px-4 text-zinc-400">
                    {tool.domain}
                  </td>
                  <td className="py-3.5 px-4 text-right font-mono text-white font-medium">
                    {tool.schema} tok
                  </td>
                  <td className="py-3.5 px-4 text-right font-mono text-zinc-400">
                    ~{tool.call} tok
                  </td>
                  <td className="py-3.5 px-4 text-right font-mono text-zinc-400">
                    ~{tool.resp} tok
                  </td>
                  <td className="py-3.5 px-4 text-right font-mono text-emerald-400 font-semibold">
                    {tool.turn} tok
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot className="bg-white/[0.02] border-t border-white/10 font-mono text-[11px]">
              <tr>
                <td colSpan={2} className="py-3 px-4 font-semibold text-white uppercase tracking-wider">
                  Total Active System Footprint
                </td>
                <td className="py-3 px-4 text-right font-bold text-emerald-400">
                  {model.clusteredSchema} tok
                </td>
                <td colSpan={2} className="py-3 px-4 text-right text-zinc-500">
                  Per-turn declaration
                </td>
                <td className="py-3 px-4 text-right font-bold text-emerald-400">
                  {model.tools.reduce((acc, t) => acc + t.turn, 0)} tok / cycle
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    </div>
  );
}
