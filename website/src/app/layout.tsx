import type { Metadata } from "next";
import "./globals.css";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

export const metadata: Metadata = {
  title: {
    default: "LearnLoop — MCP Server Engine",
    template: "%s | LearnLoop",
  },
  description:
    "Close the gap between what AI builds and what you can defend. LearnLoop is an MCP server engine that teaches developers to understand and own every line of AI-generated code.",
  keywords: ["MCP", "AI", "learning", "developer tool", "spaced repetition", "code", "agent"],
  authors: [{ name: "LearnLoop" }],
  openGraph: {
    title: "LearnLoop — MCP Server Engine",
    description: "Close the gap between what AI builds and what you can defend.",
    type: "website",
    siteName: "LearnLoop",
  },
  twitter: {
    card: "summary_large_image",
    title: "LearnLoop — MCP Server Engine",
    description: "Close the gap between what AI builds and what you can defend.",
  },
  icons: {
    icon: [
      { url: "/favicon.svg", type: "image/svg+xml" },
    ],
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@100..900&family=JetBrains+Mono:wght@100..800&family=Playfair+Display:wght@400..900&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="font-sans antialiased">
        <Navbar />
        <main>{children}</main>
        <Footer />
      </body>
    </html>
  );
}
