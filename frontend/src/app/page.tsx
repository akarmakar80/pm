"use client";

import { KanbanBoard } from "@/components/KanbanBoard";

export default function Home() {
  return (
    <main className="min-h-screen bg-slate-50 p-6">
      <KanbanBoard />
    </main>
  );
}
