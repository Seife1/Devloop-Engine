"use client";

import { useEffect, useState } from "react";
import Header, { ProjectInfo } from "@/components/Header";
import OverviewTab from "@/components/OverviewTab";
import KnowledgeCatalog from "@/components/KnowledgeCatalog";
import ReviewQueue from "@/components/ReviewQueue";
import SessionsAndEventBus from "@/components/SessionsAndEventBus";
import ServerStatus from "@/components/ServerStatus";
import DidYouKnow from "@/components/DidYouKnow";

const DEFAULT_SERVER_URL = "http://127.0.0.1:8765";

const FALLBACK_TOOLS = [
  {
    name: "track_intent",
    description: "Active coding session lifecycle, decision logging, and git commit reconciliation.",
  },
  {
    name: "manage_reviews",
    description: "Daily briefing and spaced repetition question dispatch using SM-2 algorithm.",
  },
  {
    name: "manage_knowledge",
    description: "Catalog of registered concepts, architectural invariants, and code links.",
  },
  {
    name: "explore_project",
    description: "Architectural codebase tour and verified technical facts discovery.",
  },
];

export default function DashboardPage() {
  const [serverUrl, setServerUrl] = useState(DEFAULT_SERVER_URL);
  const [isHealthy, setIsHealthy] = useState(false);
  const [version, setVersion] = useState("1.0.0");
  const [toolsCount, setToolsCount] = useState(4);
  const [dbPath, setDbPath] = useState<string | null>(null);
  const [tools, setTools] = useState(FALLBACK_TOOLS);
  const [projects, setProjects] = useState<ProjectInfo[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");
  const [activeTab, setActiveTab] = useState<"overview" | "concepts" | "reviews" | "sessions">("overview");
  const [activityLogs, setActivityLogs] = useState<string[]>([]);

  // Initialize and fetch health, projects, and tools
  const fetchData = async () => {
    try {
      const origin =
        typeof window !== "undefined" && window.location.port
          ? window.location.origin
          : DEFAULT_SERVER_URL;
      setServerUrl(origin);

      // 1. Health
      const healthRes = await fetch(`${origin}/health`);
      if (healthRes.ok) {
        const healthData = await healthRes.json();
        setIsHealthy(true);
        setVersion(healthData.version || "1.0.0");
        setToolsCount(healthData.tools_available || 4);
        setDbPath(healthData.database || null);
      } else {
        setIsHealthy(false);
      }

      // 2. Projects
      const projRes = await fetch(`${origin}/api/projects`);
      if (projRes.ok) {
        const projData = await projRes.json();
        if (projData.projects && projData.projects.length > 0) {
          setProjects(projData.projects);
          // Set initial project if none selected yet
          setSelectedProjectId((prev) => {
            if (prev && projData.projects.some((p: ProjectInfo) => p.id === prev)) {
              return prev;
            }
            // Check URL param ?p=
            if (typeof window !== "undefined") {
              const params = new URLSearchParams(window.location.search);
              const pParam = params.get("p");
              if (pParam && projData.projects.some((p: ProjectInfo) => p.id === pParam)) {
                return pParam;
              }
            }
            return projData.projects[0].id;
          });
        }
      }

      // 3. Tools
      const toolsRes = await fetch(`${origin}/tools`);
      if (toolsRes.ok) {
        const toolsData = await toolsRes.json();
        if (toolsData.tools && toolsData.tools.length > 0) {
          setTools(toolsData.tools);
          setToolsCount(toolsData.tools.length);
        }
      }
    } catch {
      setIsHealthy(false);
    }
  };

  useEffect(() => {
    fetchData();
    // Parse tab from URL
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const tabParam = params.get("tab");
      if (tabParam === "tools") {
        setActiveTab("sessions");
      } else if (tabParam && ["overview", "concepts", "reviews", "sessions"].includes(tabParam)) {
        setActiveTab(tabParam as "overview" | "concepts" | "reviews" | "sessions");
      }
    }
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleSelectProject = (id: string) => {
    setSelectedProjectId(id);
    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      url.searchParams.set("p", id);
      window.history.replaceState({}, "", url.toString());
    }
  };

  const handleSelectTab = (tab: "overview" | "concepts" | "reviews" | "sessions") => {
    setActiveTab(tab);
    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      url.searchParams.set("tab", tab);
      window.history.replaceState({}, "", url.toString());
    }
  };

  const addActivity = (msg: string) => {
    setActivityLogs((prev) => [...prev, `${new Date().toLocaleTimeString()} - ${msg}`]);
  };

  return (
    <div className="min-h-screen bg-[#0B0F19] text-[#FCFCFD] flex flex-col font-sans relative selection:bg-blue-500/30">
      {/* Top Navbar with Project Switcher */}
      <Header
        isHealthy={isHealthy}
        version={version}
        toolsCount={toolsCount}
        dbPath={dbPath}
        projects={projects}
        selectedProjectId={selectedProjectId}
        onSelectProject={handleSelectProject}
        onRefresh={fetchData}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-6 py-6 flex flex-col gap-6">
        {/* Navigation Tabs */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-white/10 pb-4 gap-4">
          <div className="flex items-center gap-1.5 font-mono text-xs overflow-x-auto">
            <button
              onClick={() => handleSelectTab("overview")}
              className={`px-4 py-2 border rounded-t transition-all cursor-pointer ${
                activeTab === "overview"
                  ? "border-emerald-500 bg-emerald-500/10 text-emerald-300 font-medium"
                  : "border-transparent text-[#94A3B8] hover:text-white"
              }`}
            >
              01 / OVERVIEW & GIT
            </button>
            <button
              onClick={() => handleSelectTab("concepts")}
              className={`px-4 py-2 border rounded-t transition-all cursor-pointer ${
                activeTab === "concepts"
                  ? "border-blue-500 bg-blue-500/10 text-blue-300 font-medium"
                  : "border-transparent text-[#94A3B8] hover:text-white"
              }`}
            >
              02 / CONCEPTS & INVARIANTS
            </button>
            <button
              onClick={() => handleSelectTab("reviews")}
              className={`px-4 py-2 border rounded-t transition-all cursor-pointer ${
                activeTab === "reviews"
                  ? "border-amber-500 bg-amber-500/10 text-amber-300 font-medium"
                  : "border-transparent text-[#94A3B8] hover:text-white"
              }`}
            >
              03 / ACTIVE RECALL (SM-2)
            </button>
            <button
              onClick={() => handleSelectTab("sessions")}
              className={`px-4 py-2 border rounded-t transition-all cursor-pointer ${
                activeTab === "sessions"
                  ? "border-purple-500 bg-purple-500/10 text-purple-300 font-medium"
                  : "border-transparent text-[#94A3B8] hover:text-white"
              }`}
            >
              04 / SESSIONS & EVENT BUS
            </button>
          </div>

          <div className="hidden sm:flex items-center gap-2 text-[11px] font-mono text-[#94A3B8]">
            <span>100% Local SQLite</span>
            <span>•</span>
            <span className="text-white">Zero Telemetry</span>
          </div>
        </div>

        {/* Tab 1: Overview & Git Telemetry */}
        {activeTab === "overview" && (
          <OverviewTab
            projectId={selectedProjectId}
            serverUrl={serverUrl}
            onNavigateToReviews={() => handleSelectTab("reviews")}
            onNavigateToConcepts={() => handleSelectTab("concepts")}
          />
        )}

        {/* Tab 2: Concepts & Invariants */}
        {activeTab === "concepts" && (
          <KnowledgeCatalog
            projectId={selectedProjectId}
            serverUrl={serverUrl}
          />
        )}

        {/* Tab 3: Active Recall Quiz Runner */}
        {activeTab === "reviews" && (
          <ReviewQueue
            projectId={selectedProjectId}
            serverUrl={serverUrl}
            onActivityLog={addActivity}
          />
        )}

        {/* Tab 4: Active Coding Sessions & Event Bus Stream */}
        {activeTab === "sessions" && (
          <SessionsAndEventBus
            projectId={selectedProjectId}
            serverUrl={serverUrl}
          />
        )}
      </main>

      {/* Floating Sticky PIP Companion Widget: Did You Know */}
      <DidYouKnow projectId={selectedProjectId} serverUrl={serverUrl} />

      <footer className="border-t border-white/10 py-6 px-6 text-center text-xs font-mono text-[#71717A] mt-auto">
        LearnLoop Developer Console • 127.0.0.1:8765 • Multi-Project Architectural Memory
      </footer>
    </div>
  );
}
