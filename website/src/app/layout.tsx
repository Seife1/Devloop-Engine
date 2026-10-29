import type { Metadata } from "next";
import { Playfair_Display, Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

const playfair = Playfair_Display({
  subsets: ["latin"],
  variable: "--font-serif",
  display: "swap",
});

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

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
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${playfair.variable} ${inter.variable} ${jetbrainsMono.variable}`}
    >
      <body className="font-sans antialiased">
        <Navbar />
        <main>{children}</main>
        <Footer />
      </body>
    </html>
  );
}
