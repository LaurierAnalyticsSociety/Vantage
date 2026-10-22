"use client";

import Link from "next/link";

export default function ErrorPage({ reset }: { reset: () => void }) {
  return <section className="panel empty-state" role="alert"><h1>Data is temporarily unavailable.</h1><p>Check that the API is running and the development database is configured, then try again.</p>
    <button className="button" onClick={reset}>Try again</button><p><Link href="/">Back to programs</Link></p></section>;
}
