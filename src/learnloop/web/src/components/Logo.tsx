"use client";

interface LogoProps {
  variant?: "dark" | "light";
  size?: "sm" | "md" | "lg";
}

export default function Logo({ variant = "dark", size = "md" }: LogoProps) {
  const isDark = variant === "dark";
  const fgColor = isDark ? "#FCFCFD" : "#0B0F19";
  const subColor = isDark ? "#94A3B8" : "#52525B";

  const markSize = size === "sm" ? 28 : size === "lg" ? 44 : 34;
  const titleSize = size === "sm" ? "text-lg" : size === "lg" ? "text-3xl" : "text-xl";
  const subSize = size === "sm" ? "text-[8px]" : size === "lg" ? "text-[11px]" : "text-[9px]";

  return (
    <div className="flex items-center gap-3 select-none">
      {/* Precision Vector Mark */}
      <svg
        width={markSize}
        height={markSize}
        viewBox="0 0 44 44"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="shrink-0"
      >
        {/* Left rounded bracket */}
        <path
          d="M 20 6 L 14 6 A 7 7 0 0 0 7 13 L 7 31 A 7 7 0 0 0 14 38 L 20 38"
          stroke={fgColor}
          strokeWidth="3.2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Right bracket with curly brace apex */}
        <path
          d="M 22 6 L 26 6 A 7 7 0 0 1 33 13 L 33 17 A 4 4 0 0 0 38 21 L 39 22 L 38 23 A 4 4 0 0 0 33 27 L 33 31 A 7 7 0 0 1 26 38 L 22 38"
          stroke={fgColor}
          strokeWidth="3.2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Prompt chevron › inside */}
        <polyline
          points="15,14 23,22 15,30"
          stroke={fgColor}
          strokeWidth="3.2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>

      {/* Typography */}
      <div className="flex flex-col justify-center">
        <span
          className={`${titleSize} font-serif tracking-tight leading-none`}
          style={{ color: fgColor }}
        >
          Learn<span className="italic font-normal">Loop</span>
        </span>
        <span
          className={`${subSize} font-mono tracking-[0.22em] uppercase mt-1 leading-none`}
          style={{ color: subColor }}
        >
          MCP SERVER ENGINE
        </span>
      </div>
    </div>
  );
}
