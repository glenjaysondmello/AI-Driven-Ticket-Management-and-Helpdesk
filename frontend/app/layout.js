import { IBM_Plex_Mono, Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-sans",
  subsets: ["latin"],
  display: "swap",
});

const ibmPlexMono = IBM_Plex_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
});

export const metadata = {
  title: "AI Helpdesk — Intelligent Support System",
  description:
    "AI-driven ticket management: 1st-line resolution, intelligent 2nd-line routing, and real-time SLA tracking.",
};

export default function RootLayout({ children }) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${ibmPlexMono.variable} h-full`}
    >
      <body className="h-full">{children}</body>
    </html>
  );
}
