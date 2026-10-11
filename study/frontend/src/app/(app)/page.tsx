"use client";

import Link from "next/link";
import SearchBox from "@/components/SearchBox";
import TopicCard from "@/components/TopicCard";
import { useApi, type LibraryEntry, type Progress } from "@/lib/api";

type Subject = { code: string; name: string; chapters: number };

export default function Dashboard() {
  const { data: library } = useApi<LibraryEntry[]>("/api/library");
  const { data: subjects } = useApi<Subject[]>("/api/subjects");
  const { data: progress } = useApi<Progress>("/api/progress");

  return (
    <div className="space-y-10">
      <section className="space-y-3">
        <h1 className="font-display text-2xl font-semibold">What do you want to study today?</h1>
        <SearchBox large />
      </section>

      {library && library.length > 0 && (
        <section className="space-y-3">
          <div className="flex items-baseline justify-between">
            <h2 className="font-display text-lg font-semibold">Continue where you left off</h2>
            <Link href="/library" className="text-sm text-brand hover:underline">See all</Link>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {library.slice(0, 4).map((t) => <TopicCard key={t.id} topic={t} />)}
          </div>
        </section>
      )}

      {progress && progress.weak.length > 0 && (
        <section className="space-y-3">
          <h2 className="font-display text-lg font-semibold">Topics to revise</h2>
          <div className="grid gap-3 sm:grid-cols-2">
            {progress.weak.slice(0, 4).map((t) => (
              <TopicCard key={t.id} topic={t} note={`${Math.round(t.accuracy * 100)}% correct in quizzes`} />
            ))}
          </div>
        </section>
      )}

      <section className="space-y-3">
        <h2 className="font-display text-lg font-semibold">Browse by subject</h2>
        <div className="grid gap-3 sm:grid-cols-3">
          {subjects?.map((s) => (
            <Link key={s.code} href={`/study/${s.code}`}
              className="rounded-lg border border-line bg-white p-4 hover:border-brand">
              <p className="font-display font-semibold">{s.name}</p>
              <p className="text-sm text-muted">{s.chapters} chapters</p>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
