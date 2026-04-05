"use client";

import { useState } from "react";
import type { BoardData } from "@/lib/kanban";

type Message = { role: "user" | "assistant"; text: string };

type AiChatWidgetProps = {
  board: BoardData;
  onBoardUpdate: (board: BoardData) => void;
  user?: string;
};

export const AiChatWidget = ({ board, onBoardUpdate, user = "user" }: AiChatWidgetProps) => {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState("");

  const sendMessage = async () => {
    if (!input.trim()) return;
    const trimmed = input.trim();
    setMessages((prev) => [...prev, { role: "user", text: trimmed }]);
    setIsSending(true);
    setError("");

    try {
      const resp = await fetch("/api/ai/kanban", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user, user_message: trimmed, board_state: board }),
      });

      if (!resp.ok) {
        const err = await resp.text();
        throw new Error(err || "AI service error");
      }

      const data = await resp.json();
      setMessages((prev) => [...prev, { role: "assistant", text: data.text_response ?? "(No response)" }]);

      if (data.board_update) {
        onBoardUpdate(data.board_update as BoardData);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setInput("");
      setIsSending(false);
    }
  };

  return (
    <aside className="w-full max-w-lg rounded-2xl border border-[var(--stroke)] bg-white p-4 shadow-[var(--shadow)]">
      <h2 className="mb-2 text-sm font-semibold text-[var(--navy-dark)]">AI Assistant</h2>
      <div className="mb-2 h-40 overflow-y-auto rounded-lg border border-[var(--stroke)] bg-slate-50 p-3">
        {messages.length === 0 ? (
          <p className="text-xs text-[var(--gray-text)]">Ask the AI to add cards or summarize the board.</p>
        ) : (
          messages.map((message, index) => (
            <div key={index} className="mb-2">
              <p className="text-xs font-medium uppercase tracking-[0.12em] text-[var(--gray-text)]">
                {message.role}
              </p>
              <p className="rounded-lg bg-white p-2 text-xs shadow-sm">{message.text}</p>
            </div>
          ))
        )}
      </div>
      {error ? <p className="mb-2 text-xs text-red-600">{error}</p> : null}
      <div className="flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          className="flex-1 rounded-md border border-[var(--stroke)] px-3 py-2 text-sm"
          placeholder="Ask AI about board updates"
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              sendMessage();
            }
          }}
        />
        <button
          onClick={sendMessage}
          disabled={isSending}
          className="rounded-md bg-[var(--primary-blue)] px-3 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
        >
          Send
        </button>
      </div>
    </aside>
  );
};
