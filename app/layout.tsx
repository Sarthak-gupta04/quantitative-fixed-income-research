import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "Quantitative Fixed-Income Strategy & Risk Dashboard",
  description:
    "An educational quantitative research project implementing a rules-based momentum and volatility-aware fixed-income strategy across U.S. Treasury ETFs, with backtesting, risk analysis, and signal decomposition.",
  keywords: [
    "quantitative finance",
    "fixed income",
    "treasury ETF",
    "backtesting",
    "momentum strategy",
    "volatility",
    "risk analysis",
    "Python",
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="bg-slate-950 text-slate-100 antialiased min-h-screen">
        {/* Top nav bar */}
        <header className="sticky top-0 z-50 border-b border-slate-800 bg-slate-950/90 backdrop-blur-md">
          <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-2 h-2 rounded-full bg-blue-400" />
              <span className="text-sm font-semibold text-slate-200 tracking-tight">
                QFI Research Dashboard
              </span>
            </div>
            <nav className="hidden md:flex items-center gap-6 text-xs text-slate-400">
              {[
                ["#executive-overview", "Overview"],
                ["#strategy", "Strategy"],
                ["#performance", "Performance"],
                ["#risk-analysis", "Risk"],
                ["#portfolio", "Portfolio"],
                ["#methodology", "Methodology"],
              ].map(([href, label]) => (
                <a
                  key={href}
                  href={href}
                  className="hover:text-slate-200 transition-colors"
                >
                  {label}
                </a>
              ))}
            </nav>
            <div className="text-xs text-slate-500 hidden md:block">
              Educational Project — Not Investment Advice
            </div>
          </div>
        </header>

        <main>{children}</main>

        {/* Footer */}
        <footer className="border-t border-slate-800 py-8 px-6 mt-16">
          <div className="max-w-7xl mx-auto">
            <div className="flex flex-col md:flex-row justify-between gap-4 text-xs text-slate-500">
              <div>
                <p className="font-medium text-slate-400 mb-1">
                  Quantitative Fixed-Income Strategy & Risk Dashboard
                </p>
                <p>
                  Educational quantitative research project. Built with Python, Next.js, and
                  Recharts.
                </p>
                <p className="mt-1">Data: Yahoo Finance (yfinance). Universe: SHY, IEF, TLT. Benchmark: AGG.</p>
              </div>
              <div className="max-w-sm text-right">
                <p className="text-amber-500/70 mb-1 font-medium">Important Disclaimer</p>
                <p>
                  All results are historical backtest statistics. Past performance does not guarantee
                  future results. This is not investment advice and is not affiliated with any
                  investment firm.
                </p>
              </div>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
