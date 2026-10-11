"use client";

import { useApi, type Platform } from "@/lib/api";

export default function SitesPage() {
  const { data } = useApi<Platform[]>("/api/platforms");
  if (!data) return null;

  // One entry per site name (YouTube has two domains).
  const sites = data.filter((p, i) => data.findIndex((q) => q.name === p.name) === i);
  const signIn = sites.filter((p) => p.login_url);
  const open = sites.filter((p) => !p.login_url);

  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <h1 className="font-display text-2xl font-semibold">Learning sites</h1>
        <p className="text-muted">
          Study Hub links only to these sites. Some of them need you to sign in before a lesson or course opens.
          Sign in on the site itself; your browser will remember it. Study Hub never asks for or stores your
          passwords for other sites. Ask your parent before creating a new account or buying a course.
        </p>
      </div>
      <section className="space-y-3">
        <h2 className="font-display text-lg font-semibold">Sites where you can sign in</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          {signIn.map((p) => (
            <div key={p.domain} className="flex items-center justify-between gap-3 rounded-lg border border-line bg-white p-4">
              <div>
                <p className="font-medium">{p.name}</p>
                <p className="text-xs text-muted">{p.note}</p>
              </div>
              <a href={p.login_url!} target="_blank" rel="noreferrer"
                className="shrink-0 rounded-md bg-brand px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-dark">
                Sign in
              </a>
            </div>
          ))}
        </div>
      </section>
      <section className="space-y-3">
        <h2 className="font-display text-lg font-semibold">No account needed</h2>
        <ul className="grid gap-2 text-sm sm:grid-cols-2">
          {open.map((p) => (
            <li key={p.domain} className="rounded-lg border border-line bg-white px-4 py-3">
              <span className="font-medium">{p.name}</span> <span className="text-muted">- {p.note}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
