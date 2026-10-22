import Link from "next/link";

export default function NotFound() {
  return <section className="panel empty-state"><h1>Page not found.</h1><p>This program or page is unavailable.</p><Link href="/">Explore programs</Link></section>;
}
