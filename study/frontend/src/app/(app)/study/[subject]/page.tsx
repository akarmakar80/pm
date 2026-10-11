"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { Suspense } from "react";
import { useApi } from "@/lib/api";

type Subject = {
  code: string;
  name: string;
  chapters: { id: number; book: string; number: number; title: string; syllabus_year: string;
    topics: { id: number; title: string }[] }[];
};

function Chapters() {
  const { subject } = useParams<{ subject: string }>();
  const { data } = useApi<Subject>(`/api/subjects/${subject}`);
  if (!data) return null;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-semibold">{data.name}</h1>
        <p className="text-sm text-muted">CBSE syllabus {data.chapters[0]?.syllabus_year}</p>
      </div>
      <div className="space-y-3">
        {data.chapters.map((c) => (
          <section key={c.id} className="rounded-lg border border-line bg-white p-4">
            <h2 className="font-display font-semibold">
              {c.book !== data.name && <span className="text-muted">{c.book} </span>}
              {c.number}. {c.title}
            </h2>
            <ul className="mt-2 flex flex-wrap gap-2">
              {c.topics.map((t) => (
                <li key={t.id}>
                  <Link href={`/topic/${t.id}`}
                    className="inline-block rounded-full border border-line px-3 py-1 text-sm hover:border-brand hover:text-brand">
                    {t.title}
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </div>
  );
}

export default function SubjectPage() {
  return (
    <Suspense>
      <Chapters />
    </Suspense>
  );
}
