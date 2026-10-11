"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

export type Role = "student" | "educator" | "parent";

export type User = { id: number; username: string; name: string; role: Role };

export type TopicSummary = {
  id: number;
  title: string;
  chapter_id: number;
  chapter_title: string;
  book: string;
  chapter_number: number;
  subject_code: string;
  subject_name: string;
};

export type Purpose = "concept" | "examples" | "application" | "reference";
export type ResourceType = "video" | "pdf" | "simulation" | "course" | "article";

export type Platform = { id?: number; name: string; domain: string; login_url: string | null; note: string };

export type Resource = {
  id: number;
  type: ResourceType;
  title: string;
  url: string;
  video_id: string | null;
  duration_sec: number | null;
  purpose: Purpose;
  source_name: string;
  badge: string;
  tier: number;
  recommendation: string | null;
  platform: Platform | null;
};

export type TopicPack = TopicSummary & {
  tabs: { learn: Resource[]; explore: Resource[]; read: Resource[]; practice: Resource[] };
};

export type SearchResult = {
  query: string;
  outcome: "match" | "choose" | "out_of_syllabus" | "blocked";
  topics: TopicSummary[];
};

export type LibraryEntry = TopicSummary & { open_count: number; last_opened_at: string };

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: init?.body ? { "Content-Type": "application/json" } : undefined,
  });
  const data = await res.json();
  if (!res.ok) {
    const detail = typeof data.detail === "string" ? data.detail : "Please check the form and try again";
    throw new ApiError(res.status, detail);
  }
  return data as T;
}

export function post<T>(path: string, body: unknown = {}): Promise<T> {
  return api<T>(path, { method: "POST", body: JSON.stringify(body) });
}

/** Fetch JSON for a component. `reload` re-runs the request. Signed-out users go to /login. */
export function useApi<T>(path: string | null) {
  const router = useRouter();
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    if (!path) return;
    let active = true;
    api<T>(path)
      .then((d) => active && (setData(d), setError(null)))
      .catch((e: ApiError) => {
        if (e.status === 401) router.replace("/login");
        else if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, [path, version, router]);

  const reload = useCallback(() => setVersion((v) => v + 1), []);
  return { data, error, reload };
}

export function formatDuration(sec: number | null): string {
  if (!sec) return "";
  const m = Math.floor(sec / 60);
  return m >= 60 ? `${Math.floor(m / 60)}h ${m % 60}m` : `${m} min`;
}

export function chapterLabel(t: TopicSummary): string {
  const chapter = `ch. ${t.chapter_number}: ${t.chapter_title}`;
  return t.book === t.subject_name ? `${t.subject_name} / ${chapter}` : `${t.subject_name} / ${t.book} ${chapter}`;
}
