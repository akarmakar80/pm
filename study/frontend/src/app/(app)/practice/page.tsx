"use client";

import Link from "next/link";
import { useState } from "react";
import StartQuiz from "@/components/StartQuiz";
import { useApi, type Progress } from "@/lib/api";

type Subject = { code: string; name: string };
type SubjectDetail = {
  name: string;
  chapters: { id: number; book: string; number: number; title: string; topics: { id: number; title: string }[] }[];
};

const chip = "rounded-full border border-line px-3 py-1 text-sm hover:border-brand hover:text-brand disabled:opacity-60";

export default function PracticePage() {
  const { data: subjects } = useApi<Subject[]>("/api/subjects");
  const { data: progress } = useApi<Progress>("/api/progress");
  const [code, setCode] = useState("maths");
  const { data: subject } = useApi<SubjectDetail>(`/api/subjects/${code}`);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-2xl font-semibold">Practice</h1>
        <p className="text-muted">
          Topic quizzes have 5 questions. Chapter tests have 10 questions with a 10-minute timer.
          You get the answers and explanations straight after you submit.
        </p>
      </div>

      {progress && progress.mistakes > 0 && (
        <section className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-accent/50 bg-accent/10 p-4">
          <p>You have <strong>{progress.mistakes}</strong> questions to retry from earlier quizzes.</p>
          <StartQuiz kind="mistakes" label="Practise my mistakes" />
        </section>
      )}

      <section className="space-y-4">
        <div className="flex flex-wrap gap-2">
          {subjects?.map((s) => (
            <button key={s.code} onClick={() => setCode(s.code)}
              className={`rounded-md px-4 py-2 text-sm font-medium ${
                code === s.code ? "bg-brand text-white" : "border border-line bg-white hover:border-brand"
              }`}>
              {s.name}
            </button>
          ))}
        </div>
        {subject?.chapters.map((c) => (
          <div key={c.id} className="space-y-3 rounded-lg border border-line bg-white p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="font-display font-semibold">
                {c.book !== subject.name && <span className="text-muted">{c.book} </span>}
                {c.number}. {c.title}
              </h2>
              <StartQuiz kind="chapter" chapterId={c.id} label="Chapter test" />
            </div>
            <div className="flex flex-wrap gap-2">
              {c.topics.map((t) => (
                <StartQuiz key={t.id} kind="topic" topicId={t.id} label={`Quiz: ${t.title}`} className={chip} />
              ))}
            </div>
          </div>
        ))}
      </section>

      {progress && progress.quizzes.length > 0 && (
        <section className="space-y-2">
          <h2 className="font-display text-lg font-semibold">Recent quizzes</h2>
          <ul className="divide-y divide-line rounded-lg border border-line bg-white">
            {progress.quizzes.slice(0, 5).map((z) => (
              <li key={z.id}>
                <Link href={`/quiz/${z.id}`} className="flex justify-between px-4 py-2 text-sm hover:bg-canvas">
                  <span>{z.title}</span>
                  <span className="text-muted">{z.score} / {z.total}</span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
