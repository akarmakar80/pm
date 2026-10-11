"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect } from "react";
import SearchBox from "@/components/SearchBox";
import TopicCard from "@/components/TopicCard";
import { useApi, type SearchResult } from "@/lib/api";

function Results() {
  const q = useSearchParams().get("q") ?? "";
  const router = useRouter();
  const { data } = useApi<SearchResult>(q ? `/api/search?q=${encodeURIComponent(q)}` : null);

  useEffect(() => {
    if (data?.outcome === "match") router.replace(`/topic/${data.topics[0].id}`);
  }, [data, router]);

  return (
    <div className="space-y-6">
      <SearchBox initial={q} />
      {data?.outcome === "choose" && (
        <section className="space-y-3">
          <h1 className="font-display text-xl font-semibold">Which topic did you mean?</h1>
          <div className="grid gap-3 sm:grid-cols-2">
            {data.topics.map((t) => <TopicCard key={t.id} topic={t} />)}
          </div>
        </section>
      )}
      {data?.outcome === "blocked" && (
        <section className="rounded-lg border border-line bg-white p-6">
          <h1 className="font-display text-xl font-semibold">This search is not available on Study Hub</h1>
          <p className="mt-2 text-muted">Try a topic or chapter name from your textbook.</p>
        </section>
      )}
      {data?.outcome === "out_of_syllabus" && (
        <section className="rounded-lg border border-line bg-white p-6">
          <h1 className="font-display text-xl font-semibold">No Class 10 topic found for &ldquo;{q}&rdquo;</h1>
          <p className="mt-2 text-muted">
            This may not be part of the current CBSE Class 10 syllabus, or it may be called something else.
            Try the chapter name or a key term from your textbook.
          </p>
        </section>
      )}
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense>
      <Results />
    </Suspense>
  );
}
