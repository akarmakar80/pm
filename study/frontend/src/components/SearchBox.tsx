"use client";

import { useRouter } from "next/navigation";

export default function SearchBox({ initial = "", large = false }: { initial?: string; large?: boolean }) {
  const router = useRouter();

  function submit(form: FormData) {
    const q = String(form.get("q")).trim();
    if (q) router.push(`/search?q=${encodeURIComponent(q)}`);
  }

  return (
    <form action={submit} className="flex gap-2">
      <input
        name="q"
        defaultValue={initial}
        required
        placeholder="Type a topic, e.g. Ohm's law, photosynthesis, quadratic formula"
        aria-label="Topic to study"
        className={`flex-1 rounded-lg border border-line bg-white px-4 ${large ? "py-3 text-lg" : "py-2"}`}
      />
      <button className="rounded-lg bg-brand px-5 font-medium text-white hover:bg-brand-dark">Search</button>
    </form>
  );
}
