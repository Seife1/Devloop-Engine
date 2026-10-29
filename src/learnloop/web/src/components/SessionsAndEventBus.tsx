"use client";

import { useEffect, useState, useMemo } from "react";

export interface Decision {
  id: string;
  choice: string;
  alternatives: string[];
  tradeoffs: string;
  created_at: string;
}

export interface SessionItem {
  id: string;
  project_id: string;
  project_name: string;
  summary: string;
  rationale: string | null;
  commit_sha: string | null;
  status: string;
  created_at: string;
  files: string[];
  skills: string[];
  decisions: Decision[];
}

export interface EventItem {
  id: string;
  event_type: string;
  category: "session" | "decision" | "git" | "recall" | "system";
  source: string;
  project_id: string;
  project_name: string;
  summary: string;
  details: Record<string, unknown>;
  timestamp: string;
}

interface SessionsAndEventBusProps {
  projectId?: string;
  serverUrl?: string;
}

export default function SessionsAndEventBus({
  projectId,
  serverUrl = "",
}: SessionsAndEventBusProps) {
  const [sessions, setSessions] = useState<SessionItem[]>([]);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState<"both" | "sessions" | "events">("both");
  const [filterCategory, setFilterCategory] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedEventId, setExpandedEventId] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date());

  const fetchData = async () => {
    try {
      const pParam = projectId && projectId !== "all" ? `?project_id=${projectId}` : "";
      
      const [sessRes, evRes] = await Promise.all([
        fetch(`${serverUrl}/api/sessions${pParam}`),
        fetch(`${serverUrl}/api/events${pParam}`),
      ]);

      if (sessRes.ok) {
        const sData = await sessRes.json();
        setSessions(sData.sessions || []);
      }

      if (evRes.ok) {
        const eData = await evRes.json();
        setEvents(eData.events || []);
      }
      setLastRefreshed(new Date());
    } catch (err) {
      console.error("Error loading sessions & events:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 8000);
    return () => clearInterval(interval);
  }, [projectId, serverUrl]);

  // Filtered Sessions
  const filteredSessions = useMemo(() => {
    return sessions.filter((s) => {
      if (!searchQuery) return true;
      const q = searchQuery.toLowerCase();
      const inSummary = s.summary?.toLowerCase().includes(q);
      const inRationale = s.rationale?.toLowerCase().includes(q);
      const inFiles = s.files?.some((f) => f.toLowerCase().includes(q));
      const inDecisions = s.decisions?.some((d) => d.choice.toLowerCase().includes(q));
      return inSummary || inRationale || inFiles || inDecisions;
    });
  }, [sessions, searchQuery]);

  // Filtered Events
  const filteredEvents = useMemo(() => {
    return events.filter((e) => {
      const matchCat = filterCategory === "all" || e.category === filterCategory;
      if (!matchCat) return false;
      if (!searchQuery) return true;
      const q = searchQuery.toLowerCase();
      return (
        e.summary?.toLowerCase().includes(q) ||
        e.source?.toLowerCase().includes(q) ||
        e.event_type?.toLowerCase().includes(q)
      );
    });
  }, [events, filterCategory, searchQuery]);

  const totalDecisions = useMemo(() => {
    return sessions.reduce((acc, s) => acc + (s.decisions?.length || 0), 0);
  }, [sessions]);

  const reconciledCount = useMemo(() => {
    return sessions.filter((s) => s.status === "reconciled" || s.commit_sha).length;
  }, [sessions]);

  const formatTime = (isoString?: string) => {
    if (!isoString) return "just now";
    try {
      const date = new Date(isoString);
      return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    } catch {
      return isoString;
    }
  };

  const formatDate = (isoString?: string) => {
    if (!isoString) return "";
    try {
      const date = new Date(isoString);
      return date.toLocaleDateString([], { month: "short", day: "numeric" });
    } catch {
      return "";
    }
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Top Banner / Telemetry Header */}
      <div className="bg-[#121826] border border-white/10 rounded-xl p-6 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-80 h-80 bg-purple-500/5 rounded-full blur-3xl pointer-events-none" />

        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 pb-6 border-b border-white/10">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-purple-400 animate-pulse" />
              <span className="text-[10px] font-mono tracking-widest uppercase text-purple-300">
                Architectural Intent Lifecycle & Telemetry Bus
              </span>
            </div>
            <h2 className="text-xl sm:text-2xl font-serif text-white tracking-tight">
              Active Sessions & Reactive Event Bus
            </h2>
            <p className="text-xs text-[#94A3B8] font-sans mt-1 max-w-2xl leading-relaxed">
              Every coding session declared by your AI pair programmer, documented Architectural Decision Record (ADR), and background Git reconciliation stream in one unified chronicle.
            </p>
          </div>

          {/* Quick Metrics */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono text-xs">
            <div className="bg-black/30 border border-white/5 rounded-lg p-3">
              <div className="text-[10px] text-[#94A3B8] uppercase">Sessions</div>
              <div className="text-lg font-bold text-white mt-0.5">{sessions.length}</div>
              <div className="text-[10px] text-emerald-400 mt-0.5">{reconciledCount} Reconciled</div>
            </div>

            <div className="bg-black/30 border border-white/5 rounded-lg p-3">
              <div className="text-[10px] text-[#94A3B8] uppercase">Decisions (ADR)</div>
              <div className="text-lg font-bold text-purple-300 mt-0.5">{totalDecisions}</div>
              <div className="text-[10px] text-[#71717A] mt-0.5">Recorded</div>
            </div>

            <div className="bg-black/30 border border-white/5 rounded-lg p-3">
              <div className="text-[10px] text-[#94A3B8] uppercase">Bus Events</div>
              <div className="text-lg font-bold text-blue-300 mt-0.5">{events.length}</div>
              <div className="text-[10px] text-[#71717A] mt-0.5">Audited</div>
            </div>

            <div className="bg-black/30 border border-white/5 rounded-lg p-3 flex flex-col justify-between">
              <div className="text-[10px] text-[#94A3B8] uppercase">Event Stream</div>
              <div className="flex items-center gap-1.5 text-xs text-emerald-400 font-bold">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                Live Polling
              </div>
              <button
                onClick={fetchData}
                className="text-[10px] text-[#94A3B8] hover:text-white underline text-left cursor-pointer mt-1"
                title="Refresh from SQLite"
              >
                ↻ {lastRefreshed.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
              </button>
            </div>
          </div>
        </div>

        {/* Controls & Filter Bar */}
        <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4 pt-4">
          {/* View mode toggle */}
          <div className="flex items-center gap-1 bg-black/40 border border-white/10 p-1 rounded-lg font-mono text-xs">
            <button
              onClick={() => setViewMode("both")}
              className={`px-3 py-1.5 rounded-md transition-all cursor-pointer ${
                viewMode === "both"
                  ? "bg-purple-500/20 text-purple-300 border border-purple-500/30 font-semibold"
                  : "text-[#94A3B8] hover:text-white"
              }`}
            >
              Split View
            </button>
            <button
              onClick={() => setViewMode("sessions")}
              className={`px-3 py-1.5 rounded-md transition-all cursor-pointer ${
                viewMode === "sessions"
                  ? "bg-purple-500/20 text-purple-300 border border-purple-500/30 font-semibold"
                  : "text-[#94A3B8] hover:text-white"
              }`}
            >
              Sessions & ADRs ({filteredSessions.length})
            </button>
            <button
              onClick={() => setViewMode("events")}
              className={`px-3 py-1.5 rounded-md transition-all cursor-pointer ${
                viewMode === "events"
                  ? "bg-purple-500/20 text-purple-300 border border-purple-500/30 font-semibold"
                  : "text-[#94A3B8] hover:text-white"
              }`}
            >
              Event Bus ({filteredEvents.length})
            </button>
          </div>

          {/* Search and category filters */}
          <div className="flex items-center gap-2 flex-wrap">
            <input
              type="text"
              placeholder="Search summary, ADR, files..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-black/40 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-white placeholder-[#71717A] font-mono focus:outline-none focus:border-purple-500 w-48 sm:w-64"
            />

            {(viewMode === "both" || viewMode === "events") && (
              <div className="flex items-center gap-1 font-mono text-[11px]">
                {[
                  { id: "all", label: "All" },
                  { id: "session", label: "Sessions" },
                  { id: "decision", label: "ADRs" },
                  { id: "git", label: "Git" },
                  { id: "recall", label: "Recall" },
                ].map((cat) => (
                  <button
                    key={cat.id}
                    onClick={() => setFilterCategory(cat.id)}
                    className={`px-2 py-1 rounded transition-colors cursor-pointer ${
                      filterCategory === cat.id
                        ? "bg-white/15 text-white font-medium"
                        : "text-[#71717A] hover:text-[#94A3B8]"
                    }`}
                  >
                    {cat.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className={`grid gap-6 ${viewMode === "both" ? "lg:grid-cols-12" : "grid-cols-1"}`}>
        {/* Left Column: Sessions & ADR Timeline */}
        {(viewMode === "both" || viewMode === "sessions") && (
          <div className={`${viewMode === "both" ? "lg:col-span-7" : "col-span-1"} flex flex-col gap-4`}>
            <div className="flex items-center justify-between">
              <h3 className="font-serif text-lg text-white flex items-center gap-2">
                <span>Active Coding Sessions & Decision Log</span>
                <span className="text-xs font-mono text-[#94A3B8]">
                  ({filteredSessions.length})
                </span>
              </h3>
              <span className="text-[10px] font-mono text-[#71717A]">
                SQLite `intents` & `decisions`
              </span>
            </div>

            {loading ? (
              <div className="p-12 text-center text-xs font-mono text-[#94A3B8] bg-[#121826] border border-white/10 rounded-xl">
                Loading sessions from SQLite...
              </div>
            ) : filteredSessions.length === 0 ? (
              <div className="p-12 text-center text-xs font-mono text-[#94A3B8] bg-[#121826] border border-white/10 rounded-xl">
                No matching sessions found. Start building with your AI to record intents.
              </div>
            ) : (
              <div className="space-y-4">
                {filteredSessions.map((sess) => (
                  <div
                    key={sess.id}
                    className="bg-[#121826] border border-white/10 hover:border-purple-500/30 rounded-xl p-5 transition-all shadow-lg flex flex-col gap-3 relative"
                  >
                    {/* Top Row: Project, Status & Timestamp */}
                    <div className="flex items-center justify-between gap-2 text-xs font-mono">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="px-2 py-0.5 bg-blue-500/10 text-blue-300 border border-blue-500/30 rounded text-[11px] font-medium">
                          {sess.project_name}
                        </span>

                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                            sess.status === "open"
                              ? "bg-amber-500/15 text-amber-300 border border-amber-500/30"
                              : "bg-emerald-500/15 text-emerald-300 border border-emerald-500/30"
                          }`}
                        >
                          {sess.status === "open" ? "● OPEN SESSION" : "✓ RECONCILED"}
                        </span>

                        <span className="text-[#71717A] text-[10px]">
                          ID: {sess.id.slice(0, 8)}
                        </span>
                      </div>

                      <div className="text-[11px] text-[#94A3B8]">
                        {formatDate(sess.created_at)} at {formatTime(sess.created_at)}
                      </div>
                    </div>

                    {/* Summary */}
                    <div>
                      <h4 className="font-serif text-base text-white leading-snug">
                        {sess.summary}
                      </h4>
                      {sess.rationale && (
                        <p className="text-xs text-[#94A3B8] font-sans mt-1.5 leading-relaxed bg-black/20 p-2.5 rounded border-l-2 border-amber-500/50">
                          <span className="text-[10px] font-mono uppercase text-amber-400 block mb-0.5">
                            Rationale (WHY):
                          </span>
                          {sess.rationale}
                        </p>
                      )}
                    </div>

                    {/* Tracked Files */}
                    {sess.files && sess.files.length > 0 && (
                      <div className="pt-2 border-t border-white/5">
                        <span className="text-[10px] font-mono text-[#71717A] block mb-1">
                          Tracked Files ({sess.files.length}):
                        </span>
                        <div className="flex flex-wrap gap-1.5">
                          {sess.files.map((f, idx) => (
                            <span
                              key={idx}
                              className="px-2 py-0.5 bg-black/40 border border-white/10 rounded font-mono text-[10px] text-zinc-300 truncate max-w-xs"
                              title={f}
                            >
                              {f}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Architectural Decision Records (ADRs) */}
                    {sess.decisions && sess.decisions.length > 0 && (
                      <div className="mt-1 space-y-2">
                        {sess.decisions.map((dec) => (
                          <div
                            key={dec.id}
                            className="bg-[#171E2E] border border-purple-500/30 rounded-lg p-3.5 text-xs font-sans"
                          >
                            <div className="flex items-center justify-between gap-2 mb-1.5 font-mono text-[10px]">
                              <span className="text-purple-300 font-bold uppercase tracking-wider flex items-center gap-1.5">
                                <span>⚖ Architectural Decision Record (ADR)</span>
                              </span>
                              <span className="text-[#71717A]">
                                {formatTime(dec.created_at)}
                              </span>
                            </div>

                            <div className="text-white font-medium mb-1.5 text-[13px]">
                              {dec.choice}
                            </div>

                            {dec.tradeoffs && (
                              <div className="text-[11px] text-[#94A3B8] leading-relaxed mb-2 bg-black/30 p-2 rounded">
                                <span className="font-mono text-purple-400 font-semibold">Trade-offs: </span>
                                {dec.tradeoffs}
                              </div>
                            )}

                            {dec.alternatives && dec.alternatives.length > 0 && (
                              <div className="flex items-center gap-1.5 flex-wrap pt-1.5 border-t border-white/5">
                                <span className="text-[10px] font-mono text-[#71717A]">
                                  Alternatives Considered:
                                </span>
                                {dec.alternatives.map((alt, aIdx) => (
                                  <span
                                    key={aIdx}
                                    className="px-1.5 py-0.5 bg-white/5 rounded text-[10px] font-mono text-zinc-400"
                                  >
                                    {alt}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Commit link footer */}
                    {sess.commit_sha && (
                      <div className="pt-2 border-t border-white/5 flex items-center justify-between text-[11px] font-mono text-[#94A3B8]">
                        <span className="text-[#71717A]">Reconciled Git Commit:</span>
                        <span className="px-2 py-0.5 bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 rounded font-bold">
                          {sess.commit_sha.slice(0, 10)}
                        </span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Right Column: Live Event Bus Stream */}
        {(viewMode === "both" || viewMode === "events") && (
          <div className={`${viewMode === "both" ? "lg:col-span-5" : "col-span-1"} flex flex-col gap-4`}>
            <div className="flex items-center justify-between">
              <h3 className="font-serif text-lg text-white flex items-center gap-2">
                <span>System Event Bus Stream</span>
                <span className="text-xs font-mono text-blue-300">
                  ({filteredEvents.length})
                </span>
              </h3>
              <span className="text-[10px] font-mono text-emerald-400 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
                Audit Log
              </span>
            </div>

            {loading ? (
              <div className="p-12 text-center text-xs font-mono text-[#94A3B8] bg-[#121826] border border-white/10 rounded-xl">
                Loading telemetry events...
              </div>
            ) : filteredEvents.length === 0 ? (
              <div className="p-12 text-center text-xs font-mono text-[#94A3B8] bg-[#121826] border border-white/10 rounded-xl">
                No events in current filter.
              </div>
            ) : (
              <div className="bg-[#121826] border border-white/10 rounded-xl p-4 flex flex-col divide-y divide-white/5 max-h-[720px] overflow-y-auto">
                {filteredEvents.map((ev) => {
                  const isExpanded = expandedEventId === ev.id;
                  const catColor =
                    ev.category === "session"
                      ? "text-amber-400 border-amber-500/30 bg-amber-500/10"
                      : ev.category === "decision"
                      ? "text-purple-400 border-purple-500/30 bg-purple-500/10"
                      : ev.category === "git"
                      ? "text-emerald-400 border-emerald-500/30 bg-emerald-500/10"
                      : ev.category === "recall"
                      ? "text-blue-400 border-blue-500/30 bg-blue-500/10"
                      : "text-zinc-400 border-white/10 bg-white/5";

                  return (
                    <div key={ev.id} className="py-3 first:pt-0 last:pb-0 flex flex-col gap-1.5">
                      {/* Top meta */}
                      <div className="flex items-center justify-between gap-2 text-[10px] font-mono">
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <span className={`px-1.5 py-0.2 border rounded uppercase ${catColor}`}>
                            {ev.category}
                          </span>
                          <span className="text-[#94A3B8]">{ev.source}</span>
                        </div>
                        <span className="text-[#71717A]">{formatTime(ev.timestamp)}</span>
                      </div>

                      {/* Event summary */}
                      <div className="text-xs font-sans text-zinc-100 leading-snug">
                        {ev.summary}
                      </div>

                      {/* Event type & expand trigger */}
                      <div className="flex items-center justify-between text-[10px] font-mono pt-1 text-[#71717A]">
                        <span className="text-zinc-400">{ev.event_type}</span>
                        {ev.details && Object.keys(ev.details).length > 0 && (
                          <button
                            onClick={() => setExpandedEventId(isExpanded ? null : ev.id)}
                            className="hover:text-purple-300 underline cursor-pointer"
                          >
                            {isExpanded ? "Hide Payload ▲" : "View Payload ▼"}
                          </button>
                        )}
                      </div>

                      {/* Expanded JSON payload */}
                      {isExpanded && ev.details && (
                        <div className="mt-1 p-2.5 bg-black/50 border border-white/10 rounded font-mono text-[10px] text-zinc-300 overflow-x-auto">
                          <pre className="whitespace-pre-wrap">
                            {JSON.stringify(ev.details, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
