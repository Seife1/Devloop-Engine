"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import Logo from "@/components/Logo";

const NAV_LINKS = [
  { label: "DOCS", href: "/docs" },
  { label: "CHANGELOG", href: "/changelog" },
];

const GITHUB_REPO_URL = "https://github.com/Seife1/Devloop-Engine";

export default function Navbar() {
  const pathname = usePathname();
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled
          ? "bg-[#0B0F19]/95 backdrop-blur-md border-b border-white/10 shadow-lg"
          : "bg-[#0B0F19]/80 backdrop-blur-sm border-b border-white/[0.06]"
      }`}
    >
      <nav className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2 shrink-0">
          <Logo variant="dark" size="sm" />
        </Link>

        {/* Desktop links */}
        <div className="hidden md:flex items-center gap-8">
          {NAV_LINKS.map((link) => {
            const isActive =
              pathname === link.href || (link.href !== "/" && pathname?.startsWith(link.href));
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`relative text-[11px] tracking-[0.15em] font-sans transition-all duration-200 ${
                  isActive
                    ? "text-emerald-400 font-bold drop-shadow-[0_0_10px_rgba(52,211,153,0.5)]"
                    : "text-[#A1A1AA] hover:text-white"
                }`}
              >
                <span>{link.label}</span>
                {isActive && (
                  <span className="absolute -bottom-1 left-0 right-0 h-[2px] bg-emerald-400 rounded-full shadow-[0_0_8px_rgba(52,211,153,0.8)]" />
                )}
              </Link>
            );
          })}
          <Link
            href={GITHUB_REPO_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[11px] tracking-[0.15em] font-sans text-[#A1A1AA] hover:text-white transition-colors duration-200 flex items-center gap-1.5"
          >
            <span>GITHUB</span>
            <svg
              width="10"
              height="10"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="opacity-60"
            >
              <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
              <polyline points="15 3 21 3 21 9" />
              <line x1="10" y1="14" x2="21" y2="3" />
            </svg>
          </Link>
          <Link
            href="/#download"
            className="ml-2 px-3.5 py-1.5 bg-white/[0.06] hover:bg-white/[0.12] text-white text-[11px] tracking-[0.1em] font-medium font-sans border border-white/15 hover:border-white/30 backdrop-blur-sm transition-all duration-200 rounded-md"
          >
            QUICK START
          </Link>
        </div>

        {/* Mobile hamburger */}
        <button
          id="mobile-menu-btn"
          className="md:hidden text-white"
          onClick={() => setMobileOpen(!mobileOpen)}
          aria-label="Toggle menu"
        >
          <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
            {mobileOpen ? (
              <path
                fillRule="evenodd"
                d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                clipRule="evenodd"
              />
            ) : (
              <path
                fillRule="evenodd"
                d="M3 5a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM3 10a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM3 15a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z"
                clipRule="evenodd"
              />
            )}
          </svg>
        </button>
      </nav>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="md:hidden bg-[#0B0F19] border-t border-white/8 px-6 py-6 flex flex-col gap-5">
          {NAV_LINKS.map((link) => {
            const isActive =
              pathname === link.href || (link.href !== "/" && pathname?.startsWith(link.href));
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`text-[11px] tracking-[0.15em] font-sans flex items-center justify-between ${
                  isActive ? "text-emerald-400 font-bold" : "text-[#A1A1AA]"
                }`}
                onClick={() => setMobileOpen(false)}
              >
                <span>{link.label}</span>
                {isActive && <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />}
              </Link>
            );
          })}
          <Link
            href={GITHUB_REPO_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[11px] tracking-[0.15em] font-sans text-[#A1A1AA] flex items-center justify-between"
            onClick={() => setMobileOpen(false)}
          >
            <span>GITHUB</span>
            <span className="text-[10px] text-zinc-500 font-mono">↗</span>
          </Link>
          <Link
            href="/#download"
            className="text-[11px] tracking-[0.15em] font-sans text-white bg-white/[0.06] hover:bg-white/[0.12] border border-white/15 hover:border-white/30 px-4 py-2 text-center rounded-md transition-all duration-200"
            onClick={() => setMobileOpen(false)}
          >
            QUICK START
          </Link>
        </div>
      )}
    </header>
  );
}
