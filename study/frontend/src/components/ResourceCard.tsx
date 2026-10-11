"use client";

import { formatDuration, post, type Resource } from "@/lib/api";

const TYPE_LABEL: Record<Resource["type"], string> = {
  video: "Video",
  pdf: "Textbook",
  simulation: "Simulation",
  course: "Course",
  article: "Article",
};

export default function ResourceCard({ item, onReported }: { item: Resource; onReported: () => void }) {
  async function report() {
    const note = window.prompt("What is wrong with this item? (broken link, wrong topic, mistake...)");
    if (note === null) return;
    await post(`/api/resources/${item.id}/report`, { note });
    onReported();
  }

  return (
    <article className="overflow-hidden rounded-lg border border-line bg-white">
      {item.video_id && (
        <div className="aspect-video bg-black">
          <iframe
            className="h-full w-full"
            src={`https://www.youtube-nocookie.com/embed/${item.video_id}?rel=0`}
            title={item.title}
            allow="encrypted-media; picture-in-picture; fullscreen"
            allowFullScreen
          />
        </div>
      )}
      <div className="space-y-2 p-4">
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className={`rounded-full px-2 py-0.5 font-medium ${
            item.tier === 3 ? "bg-ok/15 text-ok" : "bg-brand/10 text-brand"
          }`}>
            {item.badge}
          </span>
          <span className="text-muted">{TYPE_LABEL[item.type]}</span>
          {item.duration_sec && <span className="text-muted">{formatDuration(item.duration_sec)}</span>}
        </div>
        {item.video_id ? (
          <h3 className="font-medium">{item.title}</h3>
        ) : (
          <a href={item.url} target="_blank" rel="noreferrer" className="block font-medium text-brand hover:underline">
            {item.title}
          </a>
        )}
        {item.recommendation && <p className="text-sm italic text-muted">&ldquo;{item.recommendation}&rdquo;</p>}
        <button onClick={report} className="text-xs text-muted hover:text-warn">
          Report a problem
        </button>
      </div>
    </article>
  );
}
