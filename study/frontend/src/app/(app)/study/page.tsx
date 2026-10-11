"use client";

import Link from "next/link";
import { useApi } from "@/lib/api";

type Subject = { code: string; name: string; chapters: number };

export default function StudyPage() {
  const { data } = useApi<Subject[]>("/api/subjects");
  return (
    <div className="space-y-4">
      <h1 className="font-display text-2xl font-semibold">Subjects</h1>
      <div className="grid gap-3 sm:grid-cols-3">
        {data?.map((s) => (
          <Link key={s.code} href={`/study/${s.code}`} className="rounded-lg border border-line bg-white p-4 hover:border-brand">
            <p className="font-display font-semibold">{s.name}</p>
            <p className="text-sm text-muted">{s.chapters} chapters</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
