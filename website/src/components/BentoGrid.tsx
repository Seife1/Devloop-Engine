import TokenBenchmark from "@/components/TokenBenchmark";

export default function BentoGrid() {
  return (
    <section className="py-28 px-6 bg-[#0B0F19] text-[#FCFCFD] border-t border-white/10">
      <div className="max-w-7xl mx-auto">
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-16 gap-6">
          <div>
            <div className="text-xs font-mono uppercase tracking-[0.2em] text-emerald-400 mb-3 font-semibold">
              Domain-Clustered Architecture
            </div>
            <h2 className="text-3xl sm:text-5xl font-serif text-white tracking-tight">
              Four tools. <span className="italic font-normal text-zinc-300">Infinite cognitive leverage.</span>
            </h2>
          </div>
          <p className="text-xs sm:text-sm text-zinc-400 max-w-md font-sans leading-relaxed">
            Instead of cluttering agent context with 20+ fine-grained RPCs, LearnLoop consolidates all intelligence into 4 clean domains, cutting prompt token consumption by 45%.
          </p>
        </div>

        {/* Bento Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Card 1: Large Span 2 - track_intent */}
          <div className="md:col-span-2 border border-white/10 bg-[#111827] rounded-xl p-8 sm:p-10 bento-card flex flex-col justify-between shadow-xl">
            <div>
              <div className="flex items-center justify-between mb-6">
                <span className="font-mono text-xs uppercase px-2.5 py-1 bg-white/10 text-emerald-400 font-semibold rounded">
                  01 / track_intent
                </span>
                <span className="text-[11px] font-mono text-zinc-400">ACTIVE CODING & DECISIONS</span>
              </div>
              <h3 className="text-2xl sm:text-3xl font-serif text-white mb-4">
                Intent-first tracking. <span className="italic font-normal text-zinc-300">Never log what you merely "did".</span>
              </h3>
              <p className="text-xs sm:text-sm text-zinc-400 leading-relaxed max-w-xl mb-6">
                Before your AI writes code, LearnLoop requires it to state intent and architectural tradeoffs. When choosing between alternatives (e.g. SQLite vs PostgreSQL or SSE vs WebSockets), trade-offs are permanently preserved in your local project chronicle.
              </p>
            </div>

            <div className="bg-[#0B0F19] text-[#FCFCFD] p-4 font-mono text-xs overflow-x-auto border border-white/10 rounded-lg shadow-inner">
              <div className="text-zinc-500 mb-2">// Call: track_intent(action="log_decision")</div>
              <div className="text-emerald-400">&#123;</div>
              <div className="pl-4 text-zinc-300">"choice": "Domain clustering via 4 dispatcher tools",</div>
              <div className="pl-4 text-zinc-300">"alternatives": ["20 individual flat tools", "Single monolithic RPC"],</div>
              <div className="pl-4 text-zinc-300">"tradeoffs": "45% token reduction with preserved action granularity"</div>
              <div className="text-emerald-400">&#125;</div>
            </div>
          </div>

          {/* Card 2: Col 1 - manage_reviews */}
          <div className="border border-white/10 bg-[#111827] rounded-xl p-8 bento-card flex flex-col justify-between shadow-xl">
            <div>
              <div className="flex items-center justify-between mb-6">
                <span className="font-mono text-xs uppercase px-2.5 py-1 bg-white/10 text-purple-300 font-semibold rounded">
                  02 / manage_reviews
                </span>
                <span className="text-[11px] font-mono text-zinc-400">SPACED REPETITION</span>
              </div>
              <h3 className="text-xl sm:text-2xl font-serif text-white mb-4">
                Calm daily briefing. <span className="italic font-normal text-zinc-300">Never forget why code was written.</span>
              </h3>
              <p className="text-xs text-zinc-400 leading-relaxed mb-6">
                Start your coding session with <code className="font-mono text-emerald-400 bg-white/5 px-1.5 py-0.5 rounded">manage_reviews(action="briefing")</code>. LearnLoop asks one targeted question at a time to keep your conceptual memory bulletproof.
              </p>
            </div>

            <div className="border-t border-white/10 pt-4 mt-auto">
              <div className="text-[11px] font-mono text-zinc-400 uppercase mb-1">Adaptive Intervals</div>
              <div className="text-xs text-white font-medium">SM-2 Spaced Repetition Algorithm</div>
            </div>
          </div>

          {/* Card 3: Col 1 - manage_knowledge */}
          <div className="border border-white/10 bg-[#111827] rounded-xl p-8 bento-card flex flex-col justify-between shadow-xl">
            <div>
              <div className="flex items-center justify-between mb-6">
                <span className="font-mono text-xs uppercase px-2.5 py-1 bg-white/10 text-blue-300 font-semibold rounded">
                  03 / manage_knowledge
                </span>
                <span className="text-[11px] font-mono text-zinc-400">KNOWLEDGE CATALOG</span>
              </div>
              <h3 className="text-xl sm:text-2xl font-serif text-white mb-4">
                Living concepts. <span className="italic font-normal text-zinc-300">Indexed to exact code paths.</span>
              </h3>
              <p className="text-xs text-zinc-400 leading-relaxed mb-6">
                Every component, design pattern, and subtle bug fix is registered with its target source files, conceptual band (core, periphery, advanced), and explanation prompt.
              </p>
            </div>

            <div className="border-t border-white/10 pt-4 mt-auto">
              <div className="text-[11px] font-mono text-zinc-400 uppercase mb-1">Index Granularity</div>
              <div className="text-xs text-white font-medium">Concept Key ↔ Git File Links</div>
            </div>
          </div>

          {/* Card 4: Large Span 2 - explore_project */}
          <div className="md:col-span-2 border border-white/10 bg-[#111827] rounded-xl p-8 sm:p-10 bento-card flex flex-col justify-between shadow-xl">
            <div>
              <div className="flex items-center justify-between mb-6">
                <span className="font-mono text-xs uppercase px-2.5 py-1 bg-white/10 text-emerald-400 font-semibold rounded">
                  04 / explore_project
                </span>
                <span className="text-[11px] font-mono text-zinc-400">CODEBASE WALKTHROUGH</span>
              </div>
              <h3 className="text-2xl sm:text-3xl font-serif text-white mb-4">
                Autonomous onboarding. <span className="italic font-normal text-zinc-300">Zero friction for new repos.</span>
              </h3>
              <p className="text-xs sm:text-sm text-zinc-400 leading-relaxed max-w-xl mb-6">
                New to a repository or bringing in an AI teammate? <code className="font-mono text-emerald-400 bg-white/5 px-1.5 py-0.5 rounded">explore_project(action="tour")</code> provides architectural tours, technical insights ("Did You Know?"), and readiness diagnostics in milliseconds.
              </p>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 pt-4 border-t border-white/10 text-xs">
              <div>
                <span className="block font-mono text-[10px] text-zinc-500 uppercase">Action: tour</span>
                <span className="text-white font-medium">Architecture Map</span>
              </div>
              <div>
                <span className="block font-mono text-[10px] text-zinc-500 uppercase">Action: add_fact</span>
                <span className="text-white font-medium">Technical Curiosities</span>
              </div>
              <div>
                <span className="block font-mono text-[10px] text-zinc-500 uppercase">Action: readiness</span>
                <span className="text-white font-medium">Cognitive Scorecard</span>
              </div>
            </div>
          </div>
        </div>

        {/* Empirical Token Efficiency Benchmark */}
        <TokenBenchmark />
      </div>
    </section>
  );
}
