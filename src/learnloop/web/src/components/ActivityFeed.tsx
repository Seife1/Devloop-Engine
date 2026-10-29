"use client";

import { useEffect, useState } from "react";

interface ActivityItem {
  id: string;
  time: string;
  type: "tool_call" | "decision" | "commit" | "review";
  message: string;
  details?: string;
}

interface ActivityFeedProps {
  logs: string[];
}

export default function ActivityFeed({ logs }: ActivityFeedProps) {
  const [activities, setActivities] = useState<ActivityItem[]>([
    {
      id: "act-1",
      time: "Just now",
      type: "tool_call",
      message: "Server heartbeat acknowledged",
      details: "GET /health • 200 OK",
    },
    {
      id: "act-2",
      time: "2 mins ago",
      type: "decision",
      message: "Architectural decision logged",
      details: "choice='Domain-Clustered MCP' • 4 dispatchers",
    },
    {
      id: "act-3",
      time: "15 mins ago",
      type: "commit",
      message: "Git post-commit hook reconciled",
      details: "HEAD commit sha: 7f8a91b • 0 unverified files",
    },
  ]);

  useEffect(() => {
    if (logs.length > 0) {
      const latest = logs[logs.length - 1];
      setActivities((prev) => [
        {
          id: "log-" + Date.now(),
          time: "Just now",
          type: "tool_call",
          message: latest,
          details: "Interactive invocation",
        },
        ...prev.slice(0, 8),
      ]);
    }
  }, [logs]);

  return (
    <div className="bg-[#121826] border border-white/10 p-6">
      <div className="flex items-center justify-between mb-6 pb-4 border-b border-white/10">
        <div>
          <span className="text-[10px] font-mono tracking-widest uppercase text-[#94A3B8]">
            Event Bus Stream
          </span>
          <h2 className="text-xl font-serif text-white tracking-tight">
            Live Activity Feed
          </h2>
        </div>
        <div className="flex items-center gap-2 text-xs font-mono">
          <span className="w-2 h-2 rounded-full bg-emerald-400 pulse-dot" />
          <span className="text-emerald-300">SSE Listening</span>
        </div>
      </div>

      <div className="space-y-3 font-mono text-xs">
        {activities.map((act) => (
          <div
            key={act.id}
            className="p-3 bg-black/30 border border-white/5 flex items-start justify-between gap-4"
          >
            <div className="flex items-start gap-3">
              <span
                className={`mt-0.5 px-1.5 py-0.5 text-[9px] uppercase tracking-wider rounded ${
                  act.type === "decision"
                    ? "bg-purple-500/20 text-purple-300 border border-purple-500/30"
                    : act.type === "commit"
                    ? "bg-blue-500/20 text-blue-300 border border-blue-500/30"
                    : "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                }`}
              >
                {act.type}
              </span>
              <div>
                <div className="text-white font-sans text-xs">{act.message}</div>
                {act.details && (
                  <div className="text-[#94A3B8] text-[11px] mt-0.5 font-mono">
                    {act.details}
                  </div>
                )}
              </div>
            </div>
            <span className="text-[10px] text-[#71717A] shrink-0">{act.time}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
