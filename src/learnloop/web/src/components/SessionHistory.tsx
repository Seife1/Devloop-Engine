"use client";

interface Session {
  id: string;
  timestamp: string;
  summary: string;
  files: string[];
  decision?: {
    choice: string;
    tradeoffs: string;
  };
  verifiedCommit: string;
}

const SAMPLE_SESSIONS: Session[] = [
  {
    id: "sess-104",
    timestamp: "Today at 05:30",
    summary: "Scaffolding Next.js marketing site and developer local dashboard",
    files: ["website/src/app/page.tsx", "src/learnloop/web/src/app/page.tsx"],
    decision: {
      choice: "Separate marketing site (hosted) from local dev dashboard (static bundled in executable)",
      tradeoffs: "Cleaner binary footprint; marketing site can be updated independently without releasing new binary versions",
    },
    verifiedCommit: "d83e1fa",
  },
  {
    id: "sess-103",
    timestamp: "Yesterday at 17:15",
    summary: "Implementing PyInstaller standalone single-binary compilation spec",
    files: ["scripts/build_binary.py", "learnloop.spec"],
    decision: {
      choice: "Include learnloop.mcp.tools.cluster in hiddenimports",
      tradeoffs: "Ensures dynamic MCP dispatchers are discovered without runtime import errors",
    },
    verifiedCommit: "4b2c890",
  },
  {
    id: "sess-102",
    timestamp: "October 20 at 14:00",
    summary: "Refactoring 20 individual MCP tools into 4 domain clusters",
    files: ["src/learnloop/mcp/tools/cluster.py", "learnloop_http.py"],
    decision: {
      choice: "Action-based routing (track_intent, manage_reviews, manage_knowledge, explore_project)",
      tradeoffs: "45% token overhead reduction with zero loss of semantic capabilities",
    },
    verifiedCommit: "9a1f4c2",
  },
];

export default function SessionHistory() {
  return (
    <div className="bg-[#121826] border border-white/10 p-6">
      <div className="flex items-center justify-between mb-6 pb-4 border-b border-white/10">
        <div>
          <span className="text-[10px] font-mono tracking-widest uppercase text-[#94A3B8]">
            Architectural Chronicle
          </span>
          <h2 className="text-xl font-serif text-white tracking-tight">
            Session History & Decision Log
          </h2>
        </div>
        <div className="text-xs font-mono text-[#94A3B8]">
          Reconciled with <span className="text-white">Git Head</span>
        </div>
      </div>

      <div className="relative border-l border-white/10 ml-4 pl-6 space-y-8">
        {SAMPLE_SESSIONS.map((sess) => (
          <div key={sess.id} className="relative">
            {/* Timeline dot */}
            <span className="absolute -left-[31px] top-1 w-2.5 h-2.5 rounded-full bg-blue-500 border-2 border-[#0B0F19]" />

            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 mb-2">
              <h3 className="font-serif text-base text-white">{sess.summary}</h3>
              <span className="text-[10px] font-mono text-[#71717A]">{sess.timestamp}</span>
            </div>

            {/* Files */}
            <div className="flex flex-wrap gap-2 mb-3">
              {sess.files.map((f, i) => (
                <span
                  key={i}
                  className="font-mono text-[10px] px-2 py-0.5 bg-black/40 border border-white/5 text-[#94A3B8]"
                >
                  {f}
                </span>
              ))}
            </div>

            {/* Decision note */}
            {sess.decision && (
              <div className="p-3 bg-black/30 border-l-2 border-purple-500 text-xs font-sans mb-2">
                <div className="text-[10px] font-mono uppercase text-purple-400 mb-1">
                  Architectural Choice
                </div>
                <div className="text-white font-medium mb-1">{sess.decision.choice}</div>
                <div className="text-[11px] text-[#94A3B8]">{sess.decision.tradeoffs}</div>
              </div>
            )}

            <div className="text-[10px] font-mono text-emerald-400 flex items-center gap-2">
              <span>✓ Verified by Commit</span>
              <code className="text-white bg-white/5 px-1">{sess.verifiedCommit}</code>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
