import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "LearnLoop Dashboard — Local MCP Engine",
  description: "Real-time MCP inspection, active sessions, knowledge catalog, and spaced repetition review.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full bg-[#0B0F19] text-[#FCFCFD]">
      <body className="min-h-full flex flex-col font-sans antialiased bg-[#0B0F19]">
        {children}
      </body>
    </html>
  );
}
