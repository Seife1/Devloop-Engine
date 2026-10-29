import Link from "next/link";
import Logo from "@/components/Logo";

export default function Footer() {
  return (
    <footer className="border-t border-white/10 bg-[#0B0F19] text-[#FCFCFD] py-16">
      <div className="max-w-7xl mx-auto px-6 grid grid-cols-1 md:grid-cols-4 gap-12">
        <div className="md:col-span-1 flex flex-col gap-4">
          <Link href="/" className="inline-block">
            <Logo variant="dark" size="sm" />
          </Link>
          <p className="text-xs text-zinc-400 leading-relaxed max-w-xs font-sans">
            Close the gap between what AI builds and what you can defend. Open-source local-first MCP server engine.
          </p>
          <div className="text-[11px] text-zinc-500 tracking-wider uppercase font-mono mt-2">
            Local-first • 0 telemetry • Open source
          </div>
        </div>

        <div>
          <h4 className="text-[11px] font-mono uppercase tracking-[0.2em] text-zinc-400 mb-4 font-semibold">Product</h4>
          <ul className="space-y-3 text-xs font-sans">
            <li>
              <Link href="/#download" className="text-zinc-300 hover:text-white transition-colors">
                Quick Start & Download
              </Link>
            </li>
            <li>
              <Link href="/docs" className="text-zinc-300 hover:text-white transition-colors">
                Documentation
              </Link>
            </li>
            <li>
              <Link href="/changelog" className="text-zinc-300 hover:text-white transition-colors">
                Changelog & Releases
              </Link>
            </li>
          </ul>
        </div>

        <div>
          <h4 className="text-[11px] font-mono uppercase tracking-[0.2em] text-zinc-400 mb-4 font-semibold">Architecture</h4>
          <ul className="space-y-3 text-xs font-sans text-zinc-400">
            <li><span className="text-emerald-400 font-mono font-semibold">track_intent</span> — Active Coding & Commits</li>
            <li><span className="text-purple-300 font-mono font-semibold">manage_reviews</span> — Spaced Repetition</li>
            <li><span className="text-blue-300 font-mono font-semibold">manage_knowledge</span> — Living Catalog</li>
            <li><span className="text-emerald-400 font-mono font-semibold">explore_project</span> — Deep Codebase Tour</li>
          </ul>
        </div>

        <div>
          <h4 className="text-[11px] font-mono uppercase tracking-[0.2em] text-zinc-400 mb-4 font-semibold">Connect</h4>
          <ul className="space-y-3 text-xs font-sans">
            <li>
              <a href="https://github.com/Seife1/Devloop-Engine" target="_blank" rel="noopener noreferrer" className="text-zinc-300 hover:text-white transition-colors">
                GitHub Repository
              </a>
            </li>
            <li>
              <a href="https://modelcontextprotocol.io" target="_blank" rel="noopener noreferrer" className="text-zinc-300 hover:text-white transition-colors">
                Model Context Protocol Spec
              </a>
            </li>
          </ul>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 mt-16 pt-8 border-t border-white/10 flex flex-col sm:flex-row items-center justify-between gap-4 text-[11px] text-zinc-500 font-sans">
        <p>© 2026 LearnLoop Engine. Built for engineers who insist on real mastery.</p>
        <p className="font-mono text-[10px] text-emerald-400">v0.6.4 • Universal MCP 1.0 Compliant</p>
      </div>
    </footer>
  );
}
