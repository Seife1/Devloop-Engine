export const metadata = {
  title: "Changelog",
  description: "Release notes and architecture progression of LearnLoop.",
};

export default function ChangelogPage() {
  const releases = [
    {
      version: "v0.7.1",
      date: "November 3, 2026",
      tag: "Latest",
      summary: "Cross-Platform Distribution Engine Hardening & Docker Containerization",
      changes: [
        "Resolved remote setup script syntax error in /setup.sh endpoint in http_server.py.",
        "Hardened setup.sh and setup.ps1 with automatic uv/pip fallback, Linux ARM64 detection, and macOS Gatekeeper codesigning.",
        "Added official production Dockerfile (Python 3.12-slim, non-root user, /data volume) and pinned requirements.txt.",
        "Streamlined terminal installer output with silent dependency resolution and prominent next-step action prompts.",
      ],
    },
    {
      version: "v0.7.0",
      date: "October 31, 2026",
      tag: "Stable",
      summary: "Universal Autonomous Agent Setup Protocol (prompt.md)",
      changes: [
        "Published self-executing instruction manual (prompt.md) enabling frontier coding agents to configure LearnLoop globally via uvx directly from GitHub.",
        "Integrated automated post-install verification loop with self-testing checks (manage_reviews) and reload notices.",
        "Featured interactive AgentSetupCard in website Hero with badges for Claude, Cursor, Windsurf, Antigravity, and Copilot.",
      ],
    },
    {
      version: "v0.6.4",
      date: "October 29, 2026",
      tag: "Stable",
      summary: "Terminal-First ASCII Architecture Specification & Navigation Polish",
      changes: [
        "Streamlined the 'One protocol. Every editor on your machine.' section to showcase a dedicated, high-contrast ASCII architecture specification with instant 1-click clipboard copying.",
        "Removed external image dependencies and view toggle tabs in favor of a clean, terminal-first developer experience.",
        "Active route awareness in top navigation bar with glowing emerald green indicators.",
        "Synchronized all repository and release links directly to github.com/Seife1/Devloop-Engine.",
      ],
    },
    {
      version: "v0.6.3",
      date: "October 29, 2026",
      tag: "Stable",
      summary: "Empirical Token Efficiency Benchmark across Frontier Models",
      changes: [
        "Conducted empirical token counting across model tokenizers (Claude 3.5 Sonnet, GPT-4o / o1, Gemini 1.5/2.0 Pro, and DeepSeek-V3 / Llama 3) for all 4 domain-clustered tools.",
        "Added interactive TokenBenchmark component to homepage Bento Grid and Developer Documentation (/docs).",
        "Demonstrated 2,091–2,288 baseline tokens/turn across the 4 clusters vs 2,680–2,950 for legacy 17 flat tools (saving up to 24.0% system prompt overhead per turn).",
        "Empirically validated ~45% reduction in multi-turn conversation context churn.",
      ],
    },
    {
      version: "v0.6.2",
      date: "October 29, 2026",
      tag: "Stable",
      summary: "Dynamic Installation Origin & Local Clone First Setup",
      changes: [
        "Decoupled setup scripts from hardcoded domain references across the marketing website (DownloadSection.tsx) and developer documentation (QuickstartCommands.tsx) using the client-side useOrigin hook.",
        "Install commands dynamically adapt to whichever host or port serves the page (e.g. localhost, preview URLs, or production domains).",
        "Reoriented root README.md quickstart instructions to prioritize local repository scripts (.\\setup.ps1 and ./setup.sh) and local pip development.",
        "Restored signature luminous bottom curved horizon on an isolated background layer with 100% opacity dark button dock.",
      ],
    },
    {
      version: "v0.6.1",
      date: "October 28, 2026",
      tag: "Stable",
      summary: "Visual Architecture Flow & Dark Glass Dock",
      changes: [
        "Restored the signature dramatic bottom curved mask shadow transitioning seamlessly into the light page below.",
        "Framed CTA buttons inside an elevated frosted dark glass dock for razor-sharp focus and zero wash-out.",
        "Implemented alternating dark and light rhythmic section pattern across the homepage.",
        "Streamlined download switcher to focus exclusively on target OS binaries (Windows, macOS, Linux) with 1-click shell commands.",
      ],
    },
    {
      version: "v0.6.0",
      date: "October 28, 2026",
      tag: "Stable",
      summary: "100% Zero-Workspace-Pollution 'Ghost Mode'",
      changes: [
        "Workspace artifacts (commit queue, concept journals, terminal scripts) routed by default to isolated OS user-data storage (~/.learnloop/workspaces/<hash>/).",
        "Completely eliminated workspace directory pollution, .gitignore churn, and Git PR noise for team projects.",
        "Automatic post-commit hook setup now appends local exclusions to .git/info/exclude.",
        "Seamless legacy backwards-compatibility for existing repositories containing .learn/ folders.",
      ],
    },
    {
      version: "v0.5.3",
      date: "October 28, 2026",
      tag: "Stable",
      summary: "Marketing Website Dual-Mode Execution Showcase",
      changes: [
        "Added interactive dual-mode execution breakdown (ExecutionModes.tsx) distinguishing AI-autonomous background hygiene (~80%) from developer-initiated sparring.",
        "Added responsive Cluster Summary Matrix detailing trigger drivers, automation rules, and sample actions across all 4 tool clusters.",
        "Integrated dynamic commit drift detection in HTTP API and dashboard concept catalog with live stale invariant badges.",
        "Streamlined PyInstaller static asset packaging for standalone single-binary distribution.",
      ],
    },
  ];

  return (
    <div className="min-h-screen pt-32 pb-24 px-6 bg-[#0B0F19] text-[#FCFCFD]">
      <div className="max-w-3xl mx-auto">
        <div className="border-b border-white/10 pb-8 mb-12">
          <div className="text-xs font-mono uppercase tracking-[0.2em] text-emerald-400 mb-2 font-semibold">
            Release Chronicle
          </div>
          <h1 className="text-4xl sm:text-5xl font-serif text-white tracking-tight">
            Changelog & <span className="italic font-normal text-zinc-300">Evolution</span>
          </h1>
          <p className="text-sm text-zinc-400 mt-4 font-sans leading-relaxed">
            Every release synchronized directly with the local repository Git history and SemVer releases.
          </p>
        </div>

        <div className="space-y-8">
          {releases.map((rel) => (
            <div key={rel.version} className="border border-white/10 p-7 sm:p-8 bg-[#111827] rounded-xl shadow-xl transition-all hover:border-white/20">
              <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
                <div className="flex items-center gap-3">
                  <span className="font-mono text-base font-bold text-white">{rel.version}</span>
                  <span
                    className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded border ${
                      rel.tag === "Latest"
                        ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40 font-semibold"
                        : "bg-white/5 text-zinc-400 border-white/10"
                    }`}
                  >
                    {rel.tag}
                  </span>
                </div>
                <span className="text-xs font-mono text-zinc-400">{rel.date}</span>
              </div>

              <h2 className="font-serif text-xl text-white mb-4">{rel.summary}</h2>

              <ul className="space-y-2.5 text-xs sm:text-sm text-zinc-300 font-sans">
                {rel.changes.map((change, i) => (
                  <li key={i} className="flex items-start gap-2.5">
                    <span className="text-emerald-400 font-mono select-none font-bold">›</span>
                    <span className="leading-relaxed">{change}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
