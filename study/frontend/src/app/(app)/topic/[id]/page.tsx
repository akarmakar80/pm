"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { Suspense, useState } from "react";
import ResourceCard from "@/components/ResourceCard";
import StartQuiz from "@/components/StartQuiz";
import { chapterLabel, post, useApi, type Resource, type TopicPack } from "@/lib/api";

const TABS = [
  { key: "learn", label: "Learn" },
  { key: "explore", label: "Explore" },
  { key: "read", label: "Read" },
  { key: "practice", label: "Practice" },
] as const;

const LEARN_SECTIONS = [
  { purpose: "concept", title: "Understand the concept" },
  { purpose: "examples", title: "Worked examples" },
  { purpose: "application", title: "Real-life applications" },
] as const;

function Cards({ items, reload }: { items: Resource[]; reload: () => void }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {items.map((i) => <ResourceCard key={i.id} item={i} onChange={reload} />)}
    </div>
  );
}

function Learn({ pack, reload }: { pack: TopicPack; reload: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const items = pack.tabs.learn;

  async function findMore() {
    setBusy(true);
    setError("");
    try {
      await post(`/api/topics/${pack.id}/videos`);
      reload();
    } catch (e) {
      setError((e as Error).message);
    }
    setBusy(false);
  }

  if (!pack.videos_enabled) {
    return <p className="text-muted">Videos need a YouTube API key (YOUTUBE_API_KEY in .env). Meanwhile, use Read and Explore.</p>;
  }
  return (
    <div className="space-y-6">
      {items.length === 0 && <p className="text-muted">No suitable videos found yet.</p>}
      {LEARN_SECTIONS.map(({ purpose, title }) => {
        const section = items.filter((i) => i.purpose === purpose);
        return section.length > 0 && (
          <section key={purpose} className="space-y-3">
            <h2 className="font-display text-lg font-semibold">{title}</h2>
            <Cards items={section} reload={reload} />
          </section>
        );
      })}
      <div className="flex items-center gap-3">
        <button onClick={findMore} disabled={busy}
          className="rounded-md border border-line bg-white px-4 py-2 text-sm font-medium hover:border-brand disabled:opacity-60">
          {busy ? "Searching..." : "Find more videos"}
        </button>
        {error && <span className="text-sm text-warn">{error}</span>}
      </div>
    </div>
  );
}

function Pack() {
  const { id } = useParams<{ id: string }>();
  const { data: pack, reload } = useApi<TopicPack>(`/api/topics/${id}`);
  const [tab, setTab] = useState<(typeof TABS)[number]["key"]>("learn");
  if (!pack) return <p className="text-muted">Finding the best study material for this topic...</p>;

  const items = pack.tabs[tab];

  return (
    <div className="space-y-6">
      <div>
        <Link href={`/study/${pack.subject_code}`} className="text-sm text-muted hover:underline">
          {chapterLabel(pack)}
        </Link>
        <h1 className="font-display text-2xl font-semibold">{pack.title}</h1>
        <p className="mt-1 text-sm text-muted">Saved to your library.</p>
      </div>

      <div role="tablist" className="flex gap-1 border-b border-line">
        {TABS.map((t) => (
          <button
            key={t.key}
            role="tab"
            aria-selected={tab === t.key}
            onClick={() => setTab(t.key)}
            className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium ${
              tab === t.key ? "border-brand text-brand" : "border-transparent text-muted hover:text-ink"
            }`}
          >
            {t.label}{t.key !== "practice" && <span className="text-xs"> ({pack.tabs[t.key].length})</span>}
          </button>
        ))}
      </div>

      {tab === "learn" && <Learn pack={pack} reload={reload} />}
      {(tab === "explore" || tab === "read") && (
        items.length > 0 ? <Cards items={items} reload={reload} />
          : <p className="text-muted">{tab === "explore" ? "No simulation for this topic yet." : "No reading material yet."}</p>
      )}
      {tab === "practice" && (
        <div className="space-y-6">
          <section className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-line bg-white p-4">
            <div>
              <p className="font-medium">Quick quiz on {pack.title}</p>
              <p className="text-sm text-muted">5 multiple-choice questions with answers and explanations.</p>
            </div>
            <StartQuiz kind="topic" topicId={pack.id} label="Start quiz" />
          </section>
          <section className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-line bg-white p-4">
            <div>
              <p className="font-medium">Chapter test: {pack.chapter_title}</p>
              <p className="text-sm text-muted">10 questions across the chapter, 10-minute timer.</p>
            </div>
            <StartQuiz kind="chapter" chapterId={pack.chapter_id} label="Start chapter test" />
          </section>
          {items.length > 0 && (
            <section className="space-y-3">
              <p className="text-sm text-muted">Also solve the in-text questions and exercises in the NCERT chapter.</p>
              <Cards items={items} reload={reload} />
            </section>
          )}
        </div>
      )}
    </div>
  );
}

export default function TopicPage() {
  return (
    <Suspense>
      <Pack />
    </Suspense>
  );
}
