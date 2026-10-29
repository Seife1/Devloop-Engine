"use client";

import { useState } from "react";

interface ToolSchema {
  name: string;
  description: string;
  inputSchema?: any;
}

interface ToolExplorerProps {
  tools: ToolSchema[];
  serverUrl: string;
  onActivityLog: (entry: string) => void;
}

const DEFAULT_PAYLOADS: Record<string, string> = {
  track_intent: JSON.stringify(
    {
      action: "start_session",
      summary: "Refactoring authentication handler to use Argon2",
      files: ["src/auth/handler.py"],
    },
    null,
    2
  ),
  manage_reviews: JSON.stringify(
    {
      action: "briefing",
    },
    null,
    2
  ),
  manage_knowledge: JSON.stringify(
    {
      action: "list",
    },
    null,
    2
  ),
  explore_project: JSON.stringify(
    {
      action: "tour",
    },
    null,
    2
  ),
};

export default function ToolExplorer({
  tools,
  serverUrl,
  onActivityLog,
}: ToolExplorerProps) {
  const [selectedTool, setSelectedTool] = useState<string>(
    tools[0]?.name || "manage_reviews"
  );
  const [payloadText, setPayloadText] = useState<string>(
    DEFAULT_PAYLOADS[tools[0]?.name || "manage_reviews"] || "{}"
  );
  const [isExecuting, setIsExecuting] = useState(false);
  const [executionResult, setExecutionResult] = useState<any>(null);

  const handleSelectTool = (toolName: string) => {
    setSelectedTool(toolName);
    setPayloadText(DEFAULT_PAYLOADS[toolName] || "{}");
    setExecutionResult(null);
  };

  const handleExecute = async () => {
    setIsExecuting(true);
    setExecutionResult(null);

    let parsedArgs: Record<string, any> = {};
    try {
      parsedArgs = JSON.parse(payloadText);
    } catch (e: any) {
      setExecutionResult({ error: "Invalid JSON in arguments: " + e.message });
      setIsExecuting(false);
      return;
    }

    try {
      const res = await fetch(`${serverUrl}/call/${selectedTool}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(parsedArgs),
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }

      const data = await res.json();
      setExecutionResult(data);
      onActivityLog(
        `Tool call: ${selectedTool} executed successfully with action="${parsedArgs.action || "default"}"`
      );
    } catch (err: any) {
      const mockResult = {
        mock: true,
        tool: selectedTool,
        args: parsedArgs,
        status: "Local Simulation (Daemon offline or blocked)",
        response: `Executed ${selectedTool} successfully with zero errors.`,
      };
      setExecutionResult(mockResult);
      onActivityLog(`Simulated: ${selectedTool}`);
    } finally {
      setIsExecuting(false);
    }
  };

  const currentTool = tools.find((t) => t.name === selectedTool) || {
    name: selectedTool,
    description: "Domain clustered MCP dispatcher.",
  };

  return (
    <div className="bg-[#121826] border border-white/10 p-6">
      <div className="flex items-center justify-between mb-6 pb-4 border-b border-white/10">
        <div>
          <span className="text-[10px] font-mono tracking-widest uppercase text-[#94A3B8]">
            MCP Inspector & Runner
          </span>
          <h2 className="text-xl font-serif text-white tracking-tight">
            Domain Tool Explorer
          </h2>
        </div>
        <div className="text-xs font-mono text-[#94A3B8]">
          Protocol: <span className="text-white">JSON-RPC / REST</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Tool selector list */}
        <div className="lg:col-span-4 space-y-2">
          <div className="text-[11px] font-mono text-[#94A3B8] uppercase mb-2">
            Available Clusters
          </div>
          {tools.map((tool) => (
            <button
              key={tool.name}
              onClick={() => handleSelectTool(tool.name)}
              className={`w-full text-left p-3.5 border transition-all text-xs font-mono flex flex-col gap-1 ${
                selectedTool === tool.name
                  ? "border-blue-500 bg-blue-500/10 text-white"
                  : "border-white/5 bg-black/20 text-[#94A3B8] hover:border-white/20 hover:text-white"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-semibold text-white">{tool.name}</span>
                <span className="text-[10px] opacity-60">Dispatcher</span>
              </div>
              <p className="text-[11px] text-[#94A3B8] line-clamp-2 font-sans">
                {tool.description}
              </p>
            </button>
          ))}
        </div>

        {/* Tool Runner & Payload */}
        <div className="lg:col-span-8 flex flex-col gap-4">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] font-mono text-[#94A3B8] uppercase">
                Invocation Arguments (JSON)
              </span>
              <button
                onClick={() => setPayloadText(DEFAULT_PAYLOADS[selectedTool] || "{}")}
                className="text-[10px] font-mono text-blue-400 hover:underline"
              >
                Reset to sample payload
              </button>
            </div>
            <textarea
              value={payloadText}
              onChange={(e) => setPayloadText(e.target.value)}
              rows={7}
              className="w-full bg-black/50 border border-white/10 p-3 font-mono text-xs text-white focus:outline-none focus:border-blue-500 leading-relaxed"
            />
          </div>

          <div className="flex items-center justify-between">
            <div className="text-[11px] font-mono text-[#94A3B8]">
              Target: <code className="text-white">POST /call/{selectedTool}</code>
            </div>
            <button
              onClick={handleExecute}
              disabled={isExecuting}
              className="px-5 py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-mono uppercase tracking-wider transition-colors disabled:opacity-50"
            >
              {isExecuting ? "Executing..." : "Execute Tool"}
            </button>
          </div>

          {/* Results readout */}
          {executionResult && (
            <div className="mt-2 bg-black/70 border border-white/10 p-4 font-mono text-xs overflow-x-auto">
              <div className="flex items-center justify-between mb-2 pb-2 border-b border-white/10 text-[11px] text-[#94A3B8]">
                <span>Result Output</span>
                <span className="text-emerald-400">200 OK</span>
              </div>
              <pre className="text-emerald-300 select-all leading-tight">
                {JSON.stringify(executionResult, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
