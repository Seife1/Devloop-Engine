export default function PrivacyCore() {
  return (
    <section className="py-20 px-6 bg-[#FCFCFD] text-[#0B0F19] border-b border-zinc-200">
      <div className="max-w-7xl mx-auto">
        <div className="border border-zinc-200/80 bg-white rounded-xl p-8 sm:p-12 shadow-sm">
          <div className="flex flex-col md:flex-row md:items-end justify-between mb-12 gap-6">
            <div>
              <div className="inline-flex items-center gap-2 text-xs font-mono uppercase tracking-[0.2em] text-emerald-600 mb-3 font-semibold">
                <span className="text-base">🔒</span> Privacy Core & Zero Pollution
              </div>
              <h2 className="text-3xl sm:text-4xl font-serif text-zinc-900 tracking-tight">
                100% Local-First. <span className="italic font-normal text-zinc-500">Zero Third-Party Telemetry.</span>
              </h2>
            </div>
            <p className="text-xs sm:text-sm text-zinc-600 max-w-md font-sans leading-relaxed">
              Your source code, architectural tradeoffs, and learning history never leave your workstation.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 pt-8 border-t border-zinc-200">
            <div>
              <div className="font-mono text-xs text-emerald-600 uppercase tracking-wider mb-2">01 / SQLite on Disk</div>
              <h3 className="font-serif text-lg text-zinc-900 mb-2">Ghost Mode Storage Isolation</h3>
              <p className="text-xs text-zinc-600 leading-relaxed">
                All intent sessions, decision trees, and flashcard queues are written directly into an isolated local SQLite database (`~/.learnloop`). Workspace artifacts sit in OS user data, never polluting your Git repo.
              </p>
            </div>

            <div>
              <div className="font-mono text-xs text-emerald-600 uppercase tracking-wider mb-2">02 / Zero Ingestion Cloud</div>
              <h3 className="font-serif text-lg text-zinc-900 mb-2">No Remote Sync Required</h3>
              <p className="text-xs text-zinc-600 leading-relaxed">
                LearnLoop runs as an independent daemon or embedded MCP process over stdio/localhost SSE. No accounts, no API keys, and no network telemetry to external servers.
              </p>
            </div>

            <div>
              <div className="font-mono text-xs text-emerald-600 uppercase tracking-wider mb-2">03 / Git Hook Verification</div>
              <h3 className="font-serif text-lg text-zinc-900 mb-2">Commits Are Ground Truth</h3>
              <p className="text-xs text-zinc-600 leading-relaxed">
                The local git post-commit hook ensures that only code that actually compiles and lands in version control gets registered as validated knowledge.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
