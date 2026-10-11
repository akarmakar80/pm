"use client";

import { useState } from "react";
import { formatDuration, post, type Resource } from "@/lib/api";

const TYPE_LABEL: Record<Resource["type"], string> = {
  video: "Video",
  pdf: "Textbook",
  simulation: "Simulation",
  course: "Course",
  article: "Article",
};

export default function ResourceCard({ item, onChange }: { item: Resource; onChange: () => void }) {
  const [rating, setRating] = useState(item.rating);

  async function rate(helpful: boolean) {
    await post(`/api/resources/${item.id}/rating`, { helpful });
    setRating(helpful ? 1 : -1);
    if (!helpful) onChange();
  }

  return (
    <article className="overflow-hidden rounded-lg border border-line bg-white">
      {item.video_id && (
        <div className="aspect-video bg-black">
          <iframe
            className="h-full w-full"
            src={`https://www.youtube-nocookie.com/embed/${item.video_id}?rel=0&iv_load_policy=3`}
            title={item.title}
            allow="encrypted-media; picture-in-picture; fullscreen"
            allowFullScreen
          />
        </div>
      )}
      <div className="space-y-2 p-4">
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="rounded-full bg-brand/10 px-2 py-0.5 font-medium text-brand">{item.provider}</span>
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
        {item.platform?.login_url && (
          <p className="flex flex-wrap items-center gap-2 rounded-md bg-accent/15 px-3 py-2 text-xs">
            <span>{item.platform.note}.</span>
            <a href={item.platform.login_url} target="_blank" rel="noreferrer" className="font-medium text-brand hover:underline">
              Sign in to {item.platform.name}
            </a>
          </p>
        )}
        <div className="flex items-center gap-3 text-xs text-muted">
          <span>Was this useful?</span>
          <button onClick={() => rate(true)} aria-pressed={rating === 1}
            className={rating === 1 ? "font-semibold text-ok" : "hover:text-ok"}>
            {rating === 1 ? "Helpful (saved)" : "Helpful"}
          </button>
          <button onClick={() => rate(false)} className="hover:text-warn">Not helpful - hide it</button>
        </div>
      </div>
    </article>
  );
}
