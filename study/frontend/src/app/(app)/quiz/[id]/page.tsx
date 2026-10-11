"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import StartQuiz from "@/components/StartQuiz";
import { post, useApi, type Quiz, type QuizQuestion } from "@/lib/api";

const CONFIDENCE = ["Not at all", "A little", "Somewhat", "Mostly", "Fully"];

function secondsLeft(quiz: Quiz): number {
  const started = new Date(quiz.created_at.replace(" ", "T") + "Z").getTime();
  return Math.max(0, Math.round(quiz.time_limit_sec! - (Date.now() - started) / 1000));
}

function Timer({ quiz, onExpire }: { quiz: Quiz; onExpire: () => void }) {
  const [left, setLeft] = useState(() => secondsLeft(quiz));
  useEffect(() => {
    const id = setInterval(() => {
      const s = secondsLeft(quiz);
      setLeft(s);
      if (s === 0) {
        clearInterval(id);
        onExpire();
      }
    }, 1000);
    return () => clearInterval(id);
  }, [quiz, onExpire]);
  return (
    <span className={`rounded-md px-3 py-1 font-mono text-sm ${left < 60 ? "bg-warn/15 text-warn" : "bg-canvas"}`}>
      {Math.floor(left / 60)}:{String(left % 60).padStart(2, "0")} left
    </span>
  );
}

function Attempt({ quiz, onDone }: { quiz: Quiz; onDone: (q: Quiz) => void }) {
  const [answers, setAnswers] = useState<Record<number, number>>({});
  const answersRef = useRef(answers);
  const submitted = useRef(false);

  function choose(questionId: number, option: number) {
    answersRef.current = { ...answersRef.current, [questionId]: option };
    setAnswers(answersRef.current);
  }

  const submit = useCallback(async () => {
    if (submitted.current) return;
    submitted.current = true;
    onDone(await post<Quiz>(`/api/quizzes/${quiz.id}/submit`, { answers: answersRef.current }));
  }, [quiz.id, onDone]);

  const answered = Object.keys(answers).length;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-display text-2xl font-semibold">{quiz.title}</h1>
        {quiz.time_limit_sec && <Timer quiz={quiz} onExpire={submit} />}
      </div>
      <ol className="space-y-4">
        {quiz.questions.map((q, i) => (
          <li key={q.id} className="rounded-lg border border-line bg-white p-4">
            <p className="font-medium">{i + 1}. {q.question}</p>
            <div className="mt-3 grid gap-2">
              {q.options.map((opt, j) => (
                <label key={j} className={`flex cursor-pointer items-start gap-2 rounded-md border px-3 py-2 text-sm ${
                  answers[q.id] === j ? "border-brand bg-brand/5" : "border-line hover:border-brand/50"
                }`}>
                  <input type="radio" name={`q${q.id}`} checked={answers[q.id] === j}
                    onChange={() => choose(q.id, j)} className="mt-0.5" />
                  {opt}
                </label>
              ))}
            </div>
          </li>
        ))}
      </ol>
      <div className="flex items-center gap-4">
        <button onClick={submit} className="rounded-md bg-brand px-5 py-2 font-medium text-white hover:bg-brand-dark">
          Submit answers
        </button>
        <span className="text-sm text-muted">{answered} of {quiz.questions.length} answered</span>
      </div>
    </div>
  );
}

function ReviewQuestion({ q, index }: { q: QuizQuestion; index: number }) {
  const [flagged, setFlagged] = useState(q.flagged);

  async function flag() {
    const reason = window.prompt("What is wrong with this question? (wrong answer, unclear, not in syllabus...)");
    if (reason === null) return;
    await post(`/api/questions/${q.id}/flag`, { reason });
    setFlagged(true);
  }

  return (
    <li className={`rounded-lg border bg-white p-4 ${q.correct ? "border-ok/40" : "border-warn/40"}`}>
      <p className="font-medium">
        <span className={q.correct ? "text-ok" : "text-warn"}>{q.correct ? "Correct" : "Incorrect"}</span>
        {" - "}{index + 1}. {q.question}
      </p>
      <ul className="mt-3 grid gap-1 text-sm">
        {q.options.map((opt, j) => (
          <li key={j} className={`rounded-md px-3 py-1.5 ${
            j === q.answer_index ? "bg-ok/15 font-medium" : j === q.chosen_index ? "bg-warn/10 line-through" : ""
          }`}>
            {opt}
            {j === q.answer_index && " (correct answer)"}
            {j === q.chosen_index && j !== q.answer_index && " (your answer)"}
          </li>
        ))}
      </ul>
      {q.chosen_index == null && <p className="mt-2 text-sm text-warn">Not answered.</p>}
      <p className="mt-3 text-sm text-muted">{q.explanation}</p>
      <div className="mt-2 text-xs">
        {flagged ? <span className="text-muted">Reported - this question will not be used again.</span> : (
          <button onClick={flag} className="text-muted hover:text-warn">Report this question</button>
        )}
      </div>
    </li>
  );
}

function Results({ quiz }: { quiz: Quiz }) {
  const [confidence, setConfidence] = useState(quiz.confidence);
  const pct = Math.round((100 * (quiz.score ?? 0)) / quiz.total);

  async function rate(value: number) {
    await post(`/api/quizzes/${quiz.id}/confidence`, { value });
    setConfidence(value);
  }

  return (
    <div className="space-y-6">
      <h1 className="font-display text-2xl font-semibold">{quiz.title}</h1>
      <section className="flex flex-wrap items-center gap-6 rounded-lg border border-line bg-white p-6">
        <div>
          <p className="font-display text-4xl font-semibold">{quiz.score} / {quiz.total}</p>
          <p className="text-muted">{pct}% - {pct >= 80 ? "Excellent work!" : pct >= 60 ? "Good, keep practising." : "Revise this and try again."}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {quiz.topic_id && (
            <Link href={`/topic/${quiz.topic_id}`} className="rounded-md border border-line px-4 py-2 text-sm font-medium hover:border-brand">
              Revise the topic
            </Link>
          )}
          {quiz.kind === "topic" && <StartQuiz kind="topic" topicId={quiz.topic_id!} label="Try another quiz" />}
          {quiz.kind === "chapter" && <StartQuiz kind="chapter" chapterId={quiz.chapter_id!} label="Another chapter test" />}
          {quiz.score! < quiz.total && <StartQuiz kind="mistakes" label="Practise my mistakes"
            className="rounded-md border border-brand px-4 py-2 text-sm font-medium text-brand" />}
        </div>
      </section>
      <section className="rounded-lg border border-line bg-white p-4">
        <p className="text-sm font-medium">How well do you understand this now?</p>
        <div className="mt-2 flex flex-wrap gap-2">
          {CONFIDENCE.map((label, i) => (
            <button key={label} onClick={() => rate(i + 1)}
              className={`rounded-full border px-3 py-1 text-sm ${
                confidence === i + 1 ? "border-brand bg-brand text-white" : "border-line hover:border-brand"
              }`}>
              {label}
            </button>
          ))}
        </div>
      </section>
      <ol className="space-y-4">
        {quiz.questions.map((q, i) => <ReviewQuestion key={q.id} q={q} index={i} />)}
      </ol>
    </div>
  );
}

function QuizView() {
  const { id } = useParams<{ id: string }>();
  const { data, error } = useApi<Quiz>(`/api/quizzes/${id}`);
  const [result, setResult] = useState<Quiz | null>(null);
  if (error) return <p className="text-warn">{error}</p>;
  if (!data) return null;
  const quiz = result ?? data;
  return quiz.submitted_at ? <Results quiz={quiz} /> : <Attempt quiz={quiz} onDone={setResult} />;
}

export default function QuizPage() {
  return (
    <Suspense>
      <QuizView />
    </Suspense>
  );
}
