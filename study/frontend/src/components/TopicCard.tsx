import Link from "next/link";
import { chapterLabel, type TopicSummary } from "@/lib/api";

export default function TopicCard({ topic, note }: { topic: TopicSummary; note?: string }) {
  return (
    <Link
      href={`/topic/${topic.id}`}
      className="block rounded-lg border border-line bg-white p-4 hover:border-brand"
    >
      <p className="text-xs font-medium uppercase tracking-wide text-muted">
        {chapterLabel(topic)}
      </p>
      <p className="mt-1 font-display font-semibold">{topic.title}</p>
      {note && <p className="mt-1 text-xs text-muted">{note}</p>}
    </Link>
  );
}
