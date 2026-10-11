"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { post } from "@/lib/api";

type Props = {
  kind: "topic" | "chapter" | "mistakes";
  topicId?: number;
  chapterId?: number;
  label: string;
  className?: string;
};

export default function StartQuiz({ kind, topicId, chapterId, label, className }: Props) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function start() {
    setBusy(true);
    setError("");
    try {
      const { id } = await post<{ id: number }>("/api/quizzes", { kind, topic_id: topicId, chapter_id: chapterId });
      router.push(`/quiz/${id}`);
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }

  return (
    <span className="inline-flex flex-col gap-1">
      <button onClick={start} disabled={busy}
        className={className ?? "rounded-md bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-brand-dark disabled:opacity-60"}>
        {busy ? "Preparing questions..." : label}
      </button>
      {error && <span className="text-xs text-warn">{error}</span>}
    </span>
  );
}
