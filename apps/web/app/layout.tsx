import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "Vantage · Curriculum to career", template: "%s · Vantage" },
  description: "Explore the connection between published coursework and employer-requested skills.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>
    <a href="#main" className="skip-link">Skip to content</a>
    <header className="site-header"><div className="container header-inner">
      <Link href="/" className="brand"><span className="brand-symbol" aria-hidden="true">V</span>vantage<span className="beta">FOUNDATION</span></Link>
      <nav aria-label="Main navigation"><Link href="/">Programs</Link><Link href="/jobs">Explore jobs</Link><Link href="/methodology">Methodology</Link></nav>
    </div></header>
    <main id="main" className="container">{children}</main>
    <footer className="container site-footer"><span>A Laurier Analytics Society project in development.</span>
      <span>Coursework coverage ≠ individual proficiency.</span></footer>
  </body></html>;
}
