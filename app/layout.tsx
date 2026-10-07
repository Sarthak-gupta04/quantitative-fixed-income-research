import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import "./research-experience.css";

const geist = Geist({ subsets: ["latin"], variable: "--font-sans" });
const mono = Geist_Mono({ subsets: ["latin"], variable: "--font-mono" });

export const metadata: Metadata = {
  metadataBase: new URL("https://quantitative-fixed-income-research.vercel.app"),
  title: "Fixed-Income Strategy & Risk Research — Sarthak Gupta",
  description: "Independent quantitative research into a transparent momentum and volatility-aware Treasury allocation framework.",
  openGraph: {
    title: "Fixed-Income Strategy & Risk Research — Sarthak Gupta",
    description: "Explore historical Treasury allocations, model decisions, risk and evidence in an interactive research experience.",
    type: "website",
    url: "/",
    siteName: "QFI / Research",
  },
  twitter: { card: "summary_large_image" },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" data-scroll-behavior="smooth" className={`${geist.variable} ${mono.variable}`}>
      <body>{children}</body>
    </html>
  );
}
