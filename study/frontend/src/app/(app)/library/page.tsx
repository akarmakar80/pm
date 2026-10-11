"use client";

import TopicCard from "@/components/TopicCard";
import { useApi, type LibraryEntry } from "@/lib/api";

export default function LibraryPage() {
  const { data } = useApi<LibraryEntry[]>("/api/library");
  if (!data) return null;

  const bySubject = Object.groupBy(data, (t) => t.subject_name);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-2xl font-semibold">My Library</h1>
        <p className="text-muted">Every topic you have studied, saved here for revision.</p>
      </div>
      {data.length === 0 && <p className="text-muted">Search for a topic on the home page to start your library.</p>}
      {Object.entries(bySubject).map(([subject, topics]) => (
        <section key={subject} className="space-y-3">
          <h2 className="font-display text-lg font-semibold">{subject}</h2>
          <div className="grid gap-3 sm:grid-cols-2">
            {topics!.map((t) => (
              <TopicCard key={t.id} topic={t}
                note={`Opened ${t.open_count} ${t.open_count === 1 ? "time" : "times"}, last on ${t.last_opened_at.slice(0, 10)}`} />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
