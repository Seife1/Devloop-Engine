import Link from "next/link";
import QuickstartCommands from "@/components/QuickstartCommands";
import TokenBenchmark from "@/components/TokenBenchmark";

export const metadata = {
  title: "Documentation",
  description: "LearnLoop setup, developer workflows, CLI toolkit, and MCP architecture reference.",
};

export default function DocsPage() {
  return (
    <div className="min-h-screen pt-32 pb-24 px-6 bg-[#0B0F19] text-[#FCFCFD]">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="border-b border-white/10 pb-8 mb-12">
          <div className="text-xs font-mono uppercase tracking-[0.2em] text-emerald-400 mb-2 font-semibold">
            Developer Documentation
          </div>
          <h1 className="text-4xl sm:text-5xl font-serif text-white tracking-tight">
            System Guide & <span className="italic font-normal text-zinc-300">API Reference</span>
          </h1>
          <p className="text-sm text-zinc-400 mt-4 max-w-2xl font-sans leading-relaxed">
            Everything you need to pair effectively with LearnLoop: platform installation, project workflows (fresh vs existing repo backfill), CLI toolkit, and the 4-domain MCP architecture.
          </p>
        </div>

        {/* Content Grid */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-12">
          {/* Table of contents */}
          <aside className="md:col-span-1 hidden md:block">
            <div className="sticky top-28 space-y-4 text-xs font-sans">
              <div className="font-mono uppercase text-[10px] tracking-wider text-zinc-400 font-semibold">
                On this page
              </div>
              <ul className="space-y-2 border-l border-white/10 pl-3 text-zinc-400">
                <li><a href="#quickstart" className="hover:text-white transition-colors">1. Quickstart & Verification</a></li>
                <li><a href="#workflows" className="hover:text-white transition-colors">2. Project Workflows</a></li>
                <li><a href="#cli" className="hover:text-white transition-colors">3. CLI Toolkit Reference</a></li>
                <li><a href="#configuration" className="hover:text-white transition-colors">4. Automatic MCP Setup</a></li>
                <li><a href="#tools" className="hover:text-white transition-colors">5. Domain Tools Reference</a></li>
                <li><a href="#dashboard" className="hover:text-white transition-colors">6. Visual Mission Control</a></li>
                <li><a href="#sqlite" className="hover:text-white transition-colors">7. Ghost Mode Storage</a></li>
              </ul>
            </div>
          </aside>

          {/* Main Docs Body */}
          <div className="md:col-span-3 space-y-16 text-sm text-zinc-200 leading-relaxed">
            {/* 1. Quickstart & 60-Second Verification */}
            <section id="quickstart" className="scroll-mt-28">
              <h2 className="text-2xl font-serif mb-4 flex items-center gap-3 text-white">
                <span className="font-mono text-xs uppercase px-2 py-0.5 bg-emerald-400 text-black font-bold rounded">01</span>
                Quickstart & Verification
              </h2>
              <p className="text-zinc-400 mb-4">
                LearnLoop distributes as a compiled standalone binary with embedded SQLite and migrations. Zero Python installation or runtime dependencies required:
              </p>
              
              <QuickstartCommands />

              {/* 60-Second Verification */}
              <div className="p-4 bg-emerald-500/10 border border-emerald-500/25 rounded-xl text-xs text-emerald-300">
                <strong className="text-white font-semibold">⚡ First 60-Second Test:</strong> Open Cursor, VS Code, or Windsurf. Open your AI Chat and type <code className="font-mono text-white bg-white/10 px-1 py-0.5 rounded">/tour</code>. If the agent greets you with a codebase walkthrough, LearnLoop is active and verified!
              </div>
            </section>

            {/* 2. Project Workflows: Fresh vs Existing */}
            <section id="workflows" className="scroll-mt-28 pt-8 border-t border-white/10">
              <h2 className="text-2xl font-serif mb-4 flex items-center gap-3 text-white">
                <span className="font-mono text-xs uppercase px-2 py-0.5 bg-emerald-400 text-black font-bold rounded">02</span>
                Project Workflows: Fresh vs Existing Repos
              </h2>
              <p className="text-zinc-400 mb-6">
                LearnLoop adapts whether you are bootstrapping a brand-new project or connecting to an existing codebase with hundreds of past commits:
              </p>

              <div className="space-y-6">
                {/* Workflow A: Fresh Project */}
                <div className="border border-white/10 bg-[#111827] rounded-xl p-6 shadow-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="font-mono text-xs uppercase px-2 py-0.5 bg-white/10 text-emerald-400 rounded">
                      Workflow A
                    </span>
                    <h3 className="font-serif text-lg text-white">Fresh Project (Starting from Scratch)</h3>
                  </div>
                  <p className="text-xs text-zinc-400 mb-4 leading-relaxed">
                    Initialize your Git repository and run <code className="font-mono text-emerald-400">learnloop init</code> once in your project root:
                  </p>
                  <div className="bg-[#0B0F19] border border-white/10 rounded-lg p-3 font-mono text-xs text-emerald-400 mb-4">
                    mkdir my-app && cd my-app<br />
                    git init<br />
                    learnloop init
                  </div>
                  <ul className="text-xs space-y-1.5 text-zinc-300 font-sans">
                    <li>• <strong className="text-white">Editor Hook:</strong> Injects local MCP server entry and AI pairing rules for your active editor.</li>
                    <li>• <strong className="text-white">Ghost Mode:</strong> Routes internal queues to <code className="font-mono text-zinc-400">~/.learnloop/workspaces/&lt;hash&gt;/</code> and adds <code className="font-mono text-zinc-400">.learn/</code> to local <code className="font-mono text-zinc-400">.git/info/exclude</code> (zero repo clutter).</li>
                    <li>• <strong className="text-white">Post-Commit Hook:</strong> Installs a non-blocking hook so every commit automatically audits learning without slowing down Git.</li>
                  </ul>
                </div>

                {/* Workflow B: Existing Project */}
                <div className="border border-white/10 bg-[#111827] rounded-xl p-6 shadow-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="font-mono text-xs uppercase px-2 py-0.5 bg-white/10 text-purple-300 rounded">
                      Workflow B
                    </span>
                    <h3 className="font-serif text-lg text-white">Existing Project (With Historical Git Commits)</h3>
                  </div>
                  <p className="text-xs text-zinc-400 mb-4 leading-relaxed">
                    If your project already has commit history, ingest past work and scan dependencies to build an instant baseline readiness score:
                  </p>
                  <div className="bg-[#0B0F19] border border-white/10 rounded-lg p-3 font-mono text-xs text-purple-300 mb-4">
                    cd existing-project<br />
                    learnloop init<br />
                    learnloop backfill --limit 50<br />
                    learnloop techscan
                  </div>
                  <ul className="text-xs space-y-1.5 text-zinc-300 font-sans">
                    <li>• <strong className="text-white">Backfill Commits:</strong> Ingests past commit history (default 50 commits) to establish architectural baselines and file churn maps.</li>
                    <li>• <strong className="text-white">Techscan Discovery:</strong> Auto-detects dependencies across <code className="font-mono text-zinc-400">package.json</code>, <code className="font-mono text-zinc-400">pyproject.toml</code>, <code className="font-mono text-zinc-400">Cargo.toml</code>, or <code className="font-mono text-zinc-400">go.mod</code>.</li>
                  </ul>
                </div>
              </div>
            </section>

            {/* 3. Core CLI Toolkit */}
            <section id="cli" className="scroll-mt-28 pt-8 border-t border-white/10">
              <h2 className="text-2xl font-serif mb-4 flex items-center gap-3 text-white">
                <span className="font-mono text-xs uppercase px-2 py-0.5 bg-emerald-400 text-black font-bold rounded">03</span>
                Core CLI Toolkit Reference
              </h2>
              <p className="text-zinc-400 mb-6">
                All essential command-line tools provided by the standalone binary:
              </p>

              <div className="grid grid-cols-1 gap-4 text-xs font-mono">
                <div className="bg-[#111827] border border-white/10 rounded-xl p-4">
                  <div className="text-emerald-400 font-bold mb-1">learnloop init [--ide auto|cursor|vscode|windsurf]</div>
                  <p className="font-sans text-zinc-300">
                    Initializes LearnLoop in current repository: detects active IDE, installs non-blocking post-commit hook, and sets up Ghost Mode isolation.
                  </p>
                </div>

                <div className="bg-[#111827] border border-white/10 rounded-xl p-4">
                  <div className="text-purple-300 font-bold mb-1">learnloop backfill [--limit 50]</div>
                  <p className="font-sans text-zinc-300">
                    Scans past git commits to build the baseline concept catalog and tracked-files snapshot for existing repositories.
                  </p>
                </div>

                <div className="bg-[#111827] border border-white/10 rounded-xl p-4">
                  <div className="text-blue-300 font-bold mb-1">learnloop techscan</div>
                  <p className="font-sans text-zinc-300">
                    Parses project manifest files (npm, pip, cargo, go) to categorize technologies and seed the knowledge catalog with verified facts.
                  </p>
                </div>

                <div className="bg-[#111827] border border-white/10 rounded-xl p-4">
                  <div className="text-emerald-400 font-bold mb-1">learnloop dashboard [--gui] [--port 8765]</div>
                  <p className="font-sans text-zinc-300">
                    Launches the private local web UI or native desktop WebView2 app showing retention curves, readiness scorecards, and live drift alerts.
                  </p>
                </div>

                <div className="bg-[#111827] border border-white/10 rounded-xl p-4">
                  <div className="text-zinc-200 font-bold mb-1">learnloop doctor</div>
                  <p className="font-sans text-zinc-300">
                    Runs comprehensive diagnostic self-check: verifies SQLite integrity, migration versions, git hook execution, and active editor MCP links.
                  </p>
                </div>

                <div className="bg-[#111827] border border-white/10 rounded-xl p-4">
                  <div className="text-zinc-200 font-bold mb-1">learnloop review | learnloop briefing</div>
                  <p className="font-sans text-zinc-300">
                    Runs terminal-based flashcard spaced-repetition sessions or prints a calm 60-second summary of recent code drift and due cards.
                  </p>
                </div>
              </div>
            </section>

            {/* 4. Automatic MCP Configuration */}
            <section id="configuration" className="scroll-mt-28 pt-8 border-t border-white/10">
              <h2 className="text-2xl font-serif mb-4 flex items-center gap-3 text-white">
                <span className="font-mono text-xs uppercase px-2 py-0.5 bg-emerald-400 text-black font-bold rounded">04</span>
                Automatic MCP Configuration
              </h2>
              <div className="p-4 bg-emerald-500/10 border border-emerald-500/25 rounded-xl text-xs text-emerald-300 mb-6 leading-relaxed">
                <strong className="text-white font-semibold">⚡ 100% Automatic:</strong> When you run the installer or type <code className="font-mono text-white bg-white/10 px-1 py-0.5 rounded">learnloop init</code>, our Session-Aware IDE Detector automatically locates the editor hosting your session (Cursor, VS Code, Windsurf, Claude Desktop, Antigravity, or Zed) and configures the MCP server settings and AI companion instructions directly. <strong>No manual JSON file editing is required.</strong>
              </div>

              <h3 className="font-mono text-xs uppercase tracking-wider text-zinc-400 mb-3">
                Manual / Custom Host Configuration (Optional):
              </h3>
              <p className="text-zinc-400 mb-4 text-xs">
                If you are connecting LearnLoop to an external or custom MCP client, add the server definition manually:
              </p>

              <div className="bg-[#111827] border border-white/10 rounded-lg text-[#FCFCFD] p-4 font-mono text-xs overflow-x-auto">
                <pre>{`{
  "mcpServers": {
    "learnloop": {
      "command": "learnloop",
      "args": ["serve"]
    }
  }
}`}</pre>
              </div>
            </section>

            {/* 5. Domain-Clustered Tool Reference */}
            <section id="tools" className="scroll-mt-28 pt-8 border-t border-white/10">
              <h2 className="text-2xl font-serif mb-4 flex items-center gap-3 text-white">
                <span className="font-mono text-xs uppercase px-2 py-0.5 bg-emerald-400 text-black font-bold rounded">05</span>
                Domain-Clustered Tool Reference
              </h2>

              <div className="mb-8">
                <TokenBenchmark />
              </div>

              <div className="space-y-6">
                <div className="border border-white/10 p-6 bg-[#111827] rounded-xl shadow-lg">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
                    <h3 className="font-mono font-semibold text-sm text-white uppercase tracking-wider">
                      track_intent(action: string, ...)
                    </h3>
                    <span className="px-2.5 py-0.5 bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 rounded text-[11px] font-mono">
                      🤖 AI Autonomous (~80% Calls)
                    </span>
                  </div>
                  <p className="text-xs text-zinc-400 mb-3 leading-relaxed">
                    Primary AI workhorse. Called silently before writing code, during trade-offs, and immediately after commits.
                  </p>
                  <ul className="text-xs space-y-1.5 font-mono text-zinc-300">
                    <li>• <span className="text-emerald-400 font-semibold">action="start_session"</span> — declares intent and target files before coding</li>
                    <li>• <span className="text-emerald-400 font-semibold">action="log_decision"</span> — logs choices, rejected alternatives, and trade-offs</li>
                    <li>• <span className="text-emerald-400 font-semibold">action="reconcile"</span> — audits and links unrecorded commits</li>
                  </ul>
                </div>

                <div className="border border-white/10 p-6 bg-[#111827] rounded-xl shadow-lg">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
                    <h3 className="font-mono font-semibold text-sm text-white uppercase tracking-wider">
                      manage_reviews(action: string, ...)
                    </h3>
                    <span className="px-2.5 py-0.5 bg-purple-500/15 text-purple-300 border border-purple-500/30 rounded text-[11px] font-mono">
                      👤 Developer Triggered (/review)
                    </span>
                  </div>
                  <p className="text-xs text-zinc-400 mb-3 leading-relaxed">
                    Spaced repetition engine and daily catch-up briefings. Fires when developer asks or types <code className="text-purple-300 font-mono">/review</code> or <code className="text-purple-300 font-mono">/interview</code>.
                  </p>
                  <ul className="text-xs space-y-1.5 font-mono text-zinc-300">
                    <li>• <span className="text-purple-300 font-semibold">action="briefing"</span> — calm 60s summary of active context (greeting)</li>
                    <li>• <span className="text-purple-300 font-semibold">action="due"</span> — retrieves items due for spaced active recall</li>
                    <li>• <span className="text-purple-300 font-semibold">action="record"</span> — records user’s answer and reschedules via SM-2</li>
                    <li>• <span className="text-purple-300 font-semibold">action="snooze"</span> — temporarily pauses reviews for 1-30 days</li>
                  </ul>
                </div>

                <div className="border border-white/10 p-6 bg-[#111827] rounded-xl shadow-lg">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
                    <h3 className="font-mono font-semibold text-sm text-white uppercase tracking-wider">
                      manage_knowledge(action: string, ...)
                    </h3>
                    <span className="px-2.5 py-0.5 bg-blue-500/15 text-blue-300 border border-blue-500/30 rounded text-[11px] font-mono">
                      🔄 Split Hybrid
                    </span>
                  </div>
                  <p className="text-xs text-zinc-400 mb-3 leading-relaxed">
                    Auto-registers components passively in the background; queried when the developer inspects concepts or readiness.
                  </p>
                  <ul className="text-xs space-y-1.5 font-mono text-zinc-300">
                    <li>• <span className="text-blue-300 font-semibold">action="register"</span> — auto-registers components, bug fixes, invariants (AI Default)</li>
                    <li>• <span className="text-blue-300 font-semibold">action="list"</span> — compact listing of all known concepts (Developer)</li>
                    <li>• <span className="text-blue-300 font-semibold">action="readiness"</span> — scorecard of explained vs shaky invariants</li>
                  </ul>
                </div>

                <div className="border border-white/10 p-6 bg-[#111827] rounded-xl shadow-lg">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
                    <h3 className="font-mono font-semibold text-sm text-white uppercase tracking-wider">
                      explore_project(action: string, ...)
                    </h3>
                    <span className="px-2.5 py-0.5 bg-purple-500/15 text-purple-300 border border-purple-500/30 rounded text-[11px] font-mono">
                      👤 Developer Triggered (/tour)
                    </span>
                  </div>
                  <p className="text-xs text-zinc-400 mb-3 leading-relaxed">
                    Architectural onboarding, cognitive band tours, tech detection, and verified computing curiosities. Trigger with <code className="text-purple-300 font-mono">/tour</code>.
                  </p>
                  <ul className="text-xs space-y-1.5 font-mono text-zinc-300">
                    <li>• <span className="text-purple-300 font-semibold">action="tour"</span> — guided repo walkthrough (Basic &rarr; Intermediate &rarr; Advanced)</li>
                    <li>• <span className="text-purple-300 font-semibold">action="add_fact"</span> — records verified technical curiosities and origin lore</li>
                    <li>• <span className="text-purple-300 font-semibold">action="set_profile"</span> — customizes learner level, goal, and audience</li>
                  </ul>
                </div>
              </div>
            </section>

            {/* 6. Visual Mission Control */}
            <section id="dashboard" className="scroll-mt-28 pt-8 border-t border-white/10">
              <h2 className="text-2xl font-serif mb-4 flex items-center gap-3 text-white">
                <span className="font-mono text-xs uppercase px-2 py-0.5 bg-emerald-400 text-black font-bold rounded">06</span>
                Visual Mission Control Dashboard
              </h2>
              <p className="text-zinc-400 mb-4 leading-relaxed">
                Launch your local, offline analytics dashboard to inspect your project readiness score, spaced repetition retention curve, and pending commit queues:
              </p>
              <div className="bg-[#111827] border border-white/10 rounded-lg text-[#FCFCFD] p-4 font-mono text-xs mb-3">
                <span className="text-emerald-400 font-bold">&gt;</span> <span className="text-zinc-100">learnloop dashboard</span>
                <span className="text-zinc-500 block mt-1"># Runs locally on http://127.0.0.1:8765</span>
              </div>
              <p className="text-xs text-zinc-400">
                You can also run in a native desktop window: <code className="font-mono text-emerald-400">learnloop dashboard --gui</code>
              </p>
            </section>

            {/* 7. Local Storage & Ghost Mode */}
            <section id="sqlite" className="scroll-mt-28 pt-8 border-t border-white/10">
              <h2 className="text-2xl font-serif mb-4 flex items-center gap-3 text-white">
                <span className="font-mono text-xs uppercase px-2 py-0.5 bg-emerald-400 text-black font-bold rounded">07</span>
                Local Storage & Ghost Mode
              </h2>
              <p className="text-zinc-400 mb-4 leading-relaxed">
                By default, LearnLoop operates in <strong>Ghost Mode</strong> (Zero Workspace Pollution): workspace queues, concept logs, and terminal wrappers are placed in an isolated OS user-data directory (<code className="font-mono text-emerald-400 bg-white/5 px-1 rounded">~/.learnloop/workspaces/&lt;slug&gt;/</code>). The global learning database stays locally on disk at <code className="font-mono text-emerald-400 bg-white/5 px-1 rounded">~/.learnloop/learnloop.db</code>.
              </p>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
}
