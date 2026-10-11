"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { Suspense, useState } from "react";
import ResourceCard from "@/components/ResourceCard";
import { chapterLabel, useApi, type Resource, type TopicPack } from "@/lib/api";

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

const EMPTY: Record<(typeof TABS)[number]["key"], string> = {
  learn: "Educator-verified videos for this topic are still being reviewed. Start with the NCERT chapter in Read and the simulations in Explore.",
  explore: "No simulation is mapped to this topic yet.",
  read: "No reading material yet.",
  practice: "No practice material yet.",
};

function Cards({ items, reload }: { items: Resource[]; reload: () => void }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {items.map((i) => <ResourceCard key={i.id} item={i} onReported={reload} />)}
    </div>
  );
}

function Pack() {
  const { id } = useParams<{ id: string }>();
  const { data: pack, reload } = useApi<TopicPack>(`/api/topics/${id}`);
  const [tab, setTab] = useState<(typeof TABS)[number]["key"]>("learn");
  if (!pack) return null;

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
            {t.label} <span className="text-xs">({pack.tabs[t.key].length})</span>
          </button>
        ))}
      </div>

      {items.length === 0 && <p className="text-muted">{EMPTY[tab]}</p>}

      {tab === "learn"
        ? LEARN_SECTIONS.map(({ purpose, title }) => {
            const section = items.filter((i) => i.purpose === purpose);
            return section.length > 0 && (
              <section key={purpose} className="space-y-3">
                <h2 className="font-display text-lg font-semibold">{title}</h2>
                <Cards items={section} reload={reload} />
              </section>
            );
          })
        : items.length > 0 && (
            <>
              {tab === "practice" && (
                <p className="text-sm text-muted">Solve the in-text questions and the exercises at the end of the NCERT chapter.</p>
              )}
              <Cards items={items} reload={reload} />
            </>
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
