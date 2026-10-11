"use client";

import Link from "next/link";
import StartQuiz from "@/components/StartQuiz";
import { chapterLabel, useApi, type Progress } from "@/lib/api";

const CONFIDENCE = ["", "Not at all", "A little", "Somewhat", "Mostly", "Fully"];

function Tile({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border border-line bg-white p-4">
      <p className="font-display text-2xl font-semibold">{value}</p>
      <p className="text-sm text-muted">{label}</p>
    </div>
  );
}

export default function ProgressPage() {
  const { data } = useApi<Progress>("/api/progress");
  if (!data) return null;

  const answered = data.topics.reduce((n, t) => n + t.answered, 0);
  const correct = data.topics.reduce((n, t) => n + t.correct, 0);

  return (
    <div className="space-y-8">
      <h1 className="font-display text-2xl font-semibold">My progress</h1>
      {data.quizzes.length === 0 ? (
        <p className="text-muted">
          No quizzes yet. Open a topic and take its quiz, or go to <Link href="/practice" className="text-brand hover:underline">Practice</Link>.
        </p>
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-4">
            <Tile label="Quizzes taken" value={data.quizzes.length} />
            <Tile label="Questions answered" value={answered} />
            <Tile label="Overall accuracy" value={`${Math.round((100 * correct) / answered)}%`} />
            <Tile label="Mistakes to retry" value={data.mistakes} />
          </div>

          {data.weak.length > 0 && (
            <section className="space-y-3">
              <h2 className="font-display text-lg font-semibold">Topics to revise</h2>
              <ul className="space-y-2">
                {data.weak.map((t) => (
                  <li key={t.id} className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-warn/30 bg-white p-4">
                    <div>
                      <p className="text-xs text-muted">{chapterLabel(t)}</p>
                      <Link href={`/topic/${t.id}`} className="font-medium hover:text-brand">{t.title}</Link>
                      <p className="text-sm text-warn">{Math.round(t.accuracy * 100)}% correct</p>
                    </div>
                    <StartQuiz kind="topic" topicId={t.id} label="Quiz again" />
                  </li>
                ))}
              </ul>
            </section>
          )}

          <section className="space-y-3">
            <h2 className="font-display text-lg font-semibold">By topic</h2>
            <table className="w-full overflow-hidden rounded-lg border border-line bg-white text-sm">
              <thead className="bg-canvas text-left text-muted">
                <tr><th className="p-2">Topic</th><th className="p-2">Correct</th><th className="p-2">Accuracy</th></tr>
              </thead>
              <tbody>
                {data.topics.map((t) => (
                  <tr key={t.id} className="border-t border-line">
                    <td className="p-2"><Link href={`/topic/${t.id}`} className="hover:text-brand">{t.title}</Link></td>
                    <td className="p-2">{t.correct} / {t.answered}</td>
                    <td className={`p-2 ${t.accuracy < 0.6 ? "text-warn" : t.accuracy >= 0.8 ? "text-ok" : ""}`}>
                      {Math.round(t.accuracy * 100)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <section className="space-y-3">
            <h2 className="font-display text-lg font-semibold">Quiz history</h2>
            <ul className="divide-y divide-line rounded-lg border border-line bg-white">
              {data.quizzes.map((z) => (
                <li key={z.id}>
                  <Link href={`/quiz/${z.id}`} className="flex flex-wrap justify-between gap-2 px-4 py-2 text-sm hover:bg-canvas">
                    <span>{z.title}</span>
                    <span className="text-muted">
                      {z.score} / {z.total}
                      {z.confidence && ` - felt: ${CONFIDENCE[z.confidence]}`}
                      {" - "}{z.submitted_at?.slice(0, 10)}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        </>
      )}
    </div>
  );
}
