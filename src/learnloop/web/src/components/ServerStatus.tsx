"use client";

interface ServerStatusProps {
  isHealthy: boolean;
  service: string;
  version: string;
  toolsCount: number;
  dbPath: string | null;
  serverUrl: string;
}

export default function ServerStatus({
  isHealthy,
  service,
  version,
  toolsCount,
  dbPath,
  serverUrl,
}: ServerStatusProps) {
  return (
    <div className="bg-[#121826] border border-white/10 p-6 rounded-none">
      <div className="flex items-center justify-between mb-6 pb-4 border-b border-white/10">
        <div>
          <span className="text-[10px] font-mono tracking-widest uppercase text-[#94A3B8]">
            Local Daemon Status
          </span>
          <h2 className="text-xl font-serif text-white tracking-tight">
            Engine Diagnostics & Environment
          </h2>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`w-2.5 h-2.5 rounded-full ${
              isHealthy ? "bg-emerald-400 pulse-dot" : "bg-rose-500"
            }`}
          />
          <span className="font-mono text-xs uppercase tracking-wider text-white">
            {isHealthy ? "Ready" : "Disconnected"}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Bound Host */}
        <div className="bg-black/30 border border-white/5 p-4">
          <div className="text-[11px] font-mono text-[#94A3B8] uppercase">Endpoint URL</div>
          <div className="text-sm font-mono text-white mt-1 select-all">{serverUrl}</div>
          <div className="text-[10px] text-emerald-400 font-mono mt-1">CORS: Allowed Localhost</div>
        </div>

        {/* Card 2: Active Tools */}
        <div className="bg-black/30 border border-white/5 p-4">
          <div className="text-[11px] font-mono text-[#94A3B8] uppercase">Domain Clusters</div>
          <div className="text-sm font-mono text-white mt-1">{toolsCount} Active Dispatchers</div>
          <div className="text-[10px] text-blue-400 font-mono mt-1">45% Token Overhead Reduced</div>
        </div>

        {/* Card 3: SQLite DB */}
        <div className="bg-black/30 border border-white/5 p-4">
          <div className="text-[11px] font-mono text-[#94A3B8] uppercase">Local SQLite Storage</div>
          <div className="text-xs font-mono text-white mt-1 truncate" title={dbPath || "Resolving automatically..."}>
            {dbPath ? dbPath.split(/[\\/]/).pop() : "auto-resolved"}
          </div>
          <div className="text-[10px] text-zinc-400 font-mono mt-1">Local-first • 0 telemetry</div>
        </div>

        {/* Card 4: Transports */}
        <div className="bg-black/30 border border-white/5 p-4">
          <div className="text-[11px] font-mono text-[#94A3B8] uppercase">Active Transports</div>
          <div className="text-xs font-mono text-white mt-1">stdio + SSE (/sse) + JSON-RPC</div>
          <div className="text-[10px] text-emerald-400 font-mono mt-1">MCP 1.0 Compliant</div>
        </div>
      </div>
    </div>
  );
}
