"use client";

import { useState, useEffect } from "react";

/**
 * Returns the current website origin dynamically.
 * Prioritizes NEXT_PUBLIC_SITE_URL if configured, otherwise falls back
 * to window.location.origin in the browser, with an optional initial fallback for SSR.
 */
export function useOrigin(fallback: string = "https://<your-host>"): string {
  const [origin, setOrigin] = useState<string>(
    process.env.NEXT_PUBLIC_SITE_URL || fallback
  );

  useEffect(() => {
    if (typeof window !== "undefined") {
      setOrigin(process.env.NEXT_PUBLIC_SITE_URL || window.location.origin);
    }
  }, []);

  return origin;
}
