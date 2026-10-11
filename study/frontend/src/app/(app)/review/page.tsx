"use client";

import { useState } from "react";
import { useUser } from "@/components/Shell";
import { formatDuration, post, useApi, type Platform, type Purpose, type TopicSummary } from "@/lib/api";

type QueueItem = {
  id: number;
  type: string;
  title: string;
  url: string;
  video_id: string | null;
  duration_sec: number | null;
  engagement_score: number;
  status: "candidate" | "hidden";
  purpose: Purpose;
  source_name: string;
  searches: number;
  reports: string | null;
  topic: TopicSummary;
};

type Source = {
  id: number;
  kind: string;
  name: string;
  external_id: string | null;
  tier: number;
  approved_by: string | null;
  resources: number;
};

type SearchLog = {
  id: number;
  query: string;
  outcome: string;
  created_at: string;
  user_name: string;
  topic_title: string | null;
};

const CRITERIA = [
  ["alignment", "Syllabus alignment"],
  ["accuracy", "Factual accuracy"],
  ["clarity", "Clarity"],
  ["examples", "Examples / applications"],
  ["age_fit", "Age-appropriate"],
] as const;

const PURPOSES: Purpose[] = ["concept", "examples", "application", "reference"];

const TABS = ["Queue", "Add resource", "Channels", "Sites", "Searches"] as const;

const input = "rounded-md border border-line bg-white px-2 py-1.5 text-sm";

function TopicSelect({ topics, defaultValue }: { topics: TopicSummary[]; defaultValue?: number }) {
  const chapters = Object.groupBy(topics, (t) => `${t.subject_name} - ${t.chapter_title}`);
  return (
    <select name="topic_id" defaultValue={defaultValue ?? ""} required className={`${input} w-full`}>
      <option value="" disabled>Choose topic</option>
      {Object.entries(chapters).map(([chapter, ts]) => (
        <optgroup key={chapter} label={chapter}>
          {ts!.map((t) => <option key={t.id} value={t.id}>{t.title}</option>)}
        </optgroup>
      ))}
    </select>
  );
}

function Rubric() {
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
      {CRITERIA.map(([key, label]) => (
        <label key={key} className="text-xs text-muted">
          {label}
          <select name={key} required defaultValue="" className={`${input} mt-1 w-full`}>
            <option value="" disabled>-</option>
            {[1, 2, 3, 4, 5].map((n) => <option key={n}>{n}</option>)}
          </select>
        </label>
      ))}
    </div>
  );
}

function reviewBody(form: FormData) {
  return {
    ...Object.fromEntries(CRITERIA.map(([key]) => [key, Number(form.get(key))])),
    approve: form.get("verdict") === "approve",
    recommendation: String(form.get("recommendation") ?? ""),
    topic_id: Number(form.get("topic_id")),
    purpose: form.get("purpose"),
  };
}

function VerdictButtons() {
  return (
    <div className="flex gap-2">
      <button name="verdict" value="approve" className="rounded-md bg-ok px-4 py-1.5 text-sm font-medium text-white">
        Approve
      </button>
      <button name="verdict" value="reject" className="rounded-md border border-warn px-4 py-1.5 text-sm font-medium text-warn">
        Reject
      </button>
    </div>
  );
}

function ReviewForm({ item, topics, onDone }: { item: QueueItem; topics: TopicSummary[]; onDone: () => void }) {
  const [error, setError] = useState("");

  async function submit(form: FormData) {
    try {
      await post(`/api/review/resources/${item.id}`, reviewBody(form));
      onDone();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <article className="space-y-3 rounded-lg border border-line bg-white p-4">
      <div className="flex flex-wrap gap-4">
        {item.video_id && (
          <iframe
            className="aspect-video w-full rounded sm:w-72"
            src={`https://www.youtube-nocookie.com/embed/${item.video_id}?rel=0`}
            title={item.title}
            allowFullScreen
          />
        )}
        <div className="min-w-0 flex-1 space-y-1 text-sm">
          <a href={item.url} target="_blank" rel="noreferrer" className="font-medium text-brand hover:underline">
            {item.title}
          </a>
          <p className="text-muted">
            {item.source_name} {item.duration_sec ? `- ${formatDuration(item.duration_sec)}` : ""} - engagement{" "}
            {item.engagement_score.toFixed(2)} - topic searched {item.searches} times
          </p>
          {item.status === "hidden" && (
            <p className="rounded bg-warn/10 px-2 py-1 text-warn">Reported by student: {item.reports || "no note"}</p>
          )}
        </div>
      </div>
      <form action={submit} className="space-y-3">
        <div className="grid gap-2 sm:grid-cols-[1fr_auto]">
          <TopicSelect topics={topics} defaultValue={item.topic.id} />
          <select name="purpose" defaultValue={item.purpose} className={input}>
            {PURPOSES.map((p) => <option key={p}>{p}</option>)}
          </select>
        </div>
        <Rubric />
        <input name="recommendation" placeholder="One-line recommendation shown to the student (optional)"
          className={`${input} w-full`} />
        {error && <p className="text-sm text-warn">{error}</p>}
        <VerdictButtons />
      </form>
    </article>
  );
}

function Queue({ topics }: { topics: TopicSummary[] }) {
  const { data, reload } = useApi<QueueItem[]>("/api/review/queue");
  if (!data) return null;
  if (data.length === 0) return <p className="text-muted">Nothing waiting for review.</p>;
  return (
    <div className="space-y-4">
      <p className="text-sm text-muted">
        Approval needs every score to be 3 or higher. Reported items are hidden from the student until reviewed again.
      </p>
      {data.map((item) => <ReviewForm key={item.id} item={item} topics={topics} onDone={reload} />)}
    </div>
  );
}

function AddResource({ topics }: { topics: TopicSummary[] }) {
  const [message, setMessage] = useState("");

  async function submit(form: FormData) {
    try {
      const r = await post<{ status: string }>("/api/review/resources", {
        ...reviewBody(form),
        title: form.get("title"),
        url: form.get("url"),
        type: form.get("type"),
      });
      setMessage(`Saved as ${r.status}.`);
    } catch (e) {
      setMessage((e as Error).message);
    }
  }

  return (
    <form action={submit} className="space-y-3 rounded-lg border border-line bg-white p-4">
      <p className="text-sm text-muted">Add a video or link you recommend. Videos must be YouTube links.</p>
      <input name="title" required minLength={3} placeholder="Title" className={`${input} w-full`} />
      <input name="url" required type="url" pattern="https://.*" placeholder="https://..." className={`${input} w-full`} />
      <div className="grid gap-2 sm:grid-cols-[1fr_auto_auto]">
        <TopicSelect topics={topics} />
        <select name="type" className={input}>
          {["video", "simulation", "article", "pdf", "course"].map((t) => <option key={t}>{t}</option>)}
        </select>
        <select name="purpose" className={input}>
          {PURPOSES.map((p) => <option key={p}>{p}</option>)}
        </select>
      </div>
      <Rubric />
      <input name="recommendation" placeholder="One-line recommendation shown to the student (optional)"
        className={`${input} w-full`} />
      {message && <p className="text-sm">{message}</p>}
      <VerdictButtons />
    </form>
  );
}

function Channels() {
  const { data, reload } = useApi<Source[]>("/api/review/sources");
  const [message, setMessage] = useState("");

  async function add(form: FormData) {
    try {
      const r = await post<{ name: string }>("/api/review/sources", {
        handle: form.get("handle"),
        tier: Number(form.get("tier")),
      });
      setMessage(`Added ${r.name}.`);
      reload();
    } catch (e) {
      setMessage((e as Error).message);
    }
  }

  async function index(id: number) {
    setMessage("Indexing...");
    try {
      const r = await post<{ added: number }>(`/api/review/sources/${id}/index`);
      setMessage(`${r.added} new videos added.`);
      reload();
    } catch (e) {
      setMessage((e as Error).message);
    }
  }

  return (
    <div className="space-y-4">
      <form action={add} className="flex flex-wrap gap-2 rounded-lg border border-line bg-white p-4">
        <input name="handle" required placeholder="YouTube handle (@name) or channel ID" className={`${input} flex-1`} />
        <select name="tier" className={input}>
          <option value="3">Trusted channel - review each video</option>
          <option value="1">Official (NCERT/CBSE) - show immediately</option>
        </select>
        <button className="rounded-md bg-brand px-4 py-1.5 text-sm font-medium text-white">Allow-list channel</button>
      </form>
      {message && <p className="text-sm">{message}</p>}
      <table className="w-full overflow-hidden rounded-lg border border-line bg-white text-sm">
        <thead className="bg-canvas text-left text-muted">
          <tr><th className="p-2">Source</th><th className="p-2">Tier</th><th className="p-2">Items</th><th className="p-2" /></tr>
        </thead>
        <tbody>
          {data?.map((s) => (
            <tr key={s.id} className="border-t border-line">
              <td className="p-2">{s.name} <span className="text-muted">({s.kind})</span></td>
              <td className="p-2">{s.tier}</td>
              <td className="p-2">{s.resources}</td>
              <td className="p-2 text-right">
                {s.kind === "youtube_channel" && (
                  <button onClick={() => index(s.id)} className="text-brand hover:underline">Index now</button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Sites() {
  const user = useUser();
  const { data, reload } = useApi<Platform[]>("/api/platforms");
  const [message, setMessage] = useState("");

  async function add(form: FormData) {
    try {
      await post("/api/review/platforms", {
        domain: String(form.get("domain")).trim().toLowerCase(),
        name: form.get("name"),
        login_url: form.get("login_url") || null,
        note: form.get("note"),
      });
      setMessage("Site added.");
      reload();
    } catch (e) {
      setMessage((e as Error).message);
    }
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted">
        Links can only be added from these sites. Each item is still reviewed before the student sees it.
      </p>
      {user.role === "parent" && (
        <form action={add} className="grid gap-2 rounded-lg border border-line bg-white p-4 sm:grid-cols-2">
          <input name="domain" required placeholder="Domain, e.g. example.com" className={input} />
          <input name="name" required minLength={2} placeholder="Site name" className={input} />
          <input name="login_url" type="url" pattern="https://.*" placeholder="Sign-in page (if accounts are needed)" className={input} />
          <input name="note" placeholder="Note, e.g. Free; sign in to save progress" className={input} />
          <button className="rounded-md bg-brand px-4 py-1.5 text-sm font-medium text-white sm:col-span-2">Allow site</button>
        </form>
      )}
      {message && <p className="text-sm">{message}</p>}
      <table className="w-full rounded-lg border border-line bg-white text-sm">
        <thead className="bg-canvas text-left text-muted">
          <tr><th className="p-2">Site</th><th className="p-2">Domain</th><th className="p-2">Sign-in</th></tr>
        </thead>
        <tbody>
          {data?.map((p) => (
            <tr key={p.domain} className="border-t border-line">
              <td className="p-2">{p.name}</td>
              <td className="p-2 text-muted">{p.domain}</td>
              <td className="p-2">{p.login_url ? "Account needed or optional" : "No account"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Searches() {
  const { data } = useApi<SearchLog[]>("/api/review/searches");
  if (!data) return null;
  if (data.length === 0) return <p className="text-muted">No searches yet.</p>;
  return (
    <table className="w-full rounded-lg border border-line bg-white text-sm">
      <thead className="bg-canvas text-left text-muted">
        <tr><th className="p-2">When</th><th className="p-2">Who</th><th className="p-2">Query</th><th className="p-2">Result</th></tr>
      </thead>
      <tbody>
        {data.map((s) => (
          <tr key={s.id} className="border-t border-line">
            <td className="p-2 text-muted">{s.created_at}</td>
            <td className="p-2">{s.user_name}</td>
            <td className="p-2">{s.query}</td>
            <td className={`p-2 ${s.outcome === "out_of_syllabus" || s.outcome === "blocked" ? "text-warn" : ""}`}>
              {s.outcome === "match" ? s.topic_title : s.outcome.replaceAll("_", " ")}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function ReviewPage() {
  const [tab, setTab] = useState<(typeof TABS)[number]>("Queue");
  const { data: topics } = useApi<TopicSummary[]>("/api/topics");
  if (!topics) return null;

  return (
    <div className="space-y-6">
      <h1 className="font-display text-2xl font-semibold">Review</h1>
      <div role="tablist" className="flex gap-1 border-b border-line">
        {TABS.map((t) => (
          <button key={t} role="tab" aria-selected={tab === t} onClick={() => setTab(t)}
            className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium ${
              tab === t ? "border-brand text-brand" : "border-transparent text-muted hover:text-ink"
            }`}>
            {t}
          </button>
        ))}
      </div>
      {tab === "Queue" && <Queue topics={topics} />}
      {tab === "Add resource" && <AddResource topics={topics} />}
      {tab === "Channels" && <Channels />}
      {tab === "Sites" && <Sites />}
      {tab === "Searches" && <Searches />}
    </div>
  );
}
