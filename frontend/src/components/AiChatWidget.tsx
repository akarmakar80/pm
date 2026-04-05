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
  const [open, setOpen] = useState(false);

  const sendMessage = async () => {
    if (!input.trim()) return;
    const trimmed = input.trim();
    setMessages((prev) => [...prev, { role: "user", text: trimmed }]);
    setInput("");
    setIsSending(true);
    setError("");

    try {
      const resp = await fetch("/api/ai/kanban", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user, user_message: trimmed, board_state: board }),
      });

      if (!resp.ok) throw new Error((await resp.text()) || "AI service error");

      const data = await resp.json();
      setMessages((prev) => [...prev, { role: "assistant", text: data.text_response ?? "(No response)" }]);
      if (data.board_update) onBoardUpdate(data.board_update as BoardData);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div>
      {/* Toggle row */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => setOpen((v) => !v)}
          className="flex items-center gap-2 text-xs font-semibold text-[var(--navy-dark)] hover:text-[var(--primary-blue)] transition"
        >
          <span
            className="h-4 w-4 rounded-full flex items-center justify-center text-white text-[10px]"
            style={{ background: "var(--secondary-purple)" }}
          >
            {open ? "▾" : "▸"}
          </span>
          AI Assistant
        </button>
        {!open && messages.length > 0 && (
          <span className="text-xs text-[var(--gray-text)]">{messages.length} message{messages.length !== 1 ? "s" : ""}</span>
        )}
        {/* Inline input when collapsed */}
        {!open && (
          <div className="flex flex-1 gap-2 max-w-lg">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
              className="flex-1 text-xs rounded-md border border-[var(--stroke)] px-3 py-1.5 outline-none focus:border-[var(--primary-blue)]"
              placeholder="Ask AI to update your board..."
            />
            <button
              onClick={sendMessage}
              disabled={isSending}
              className="text-xs font-semibold px-3 py-1.5 rounded-md text-white transition disabled:opacity-50"
              style={{ background: "var(--secondary-purple)" }}
            >
              {isSending ? "..." : "Send"}
            </button>
          </div>
        )}
      </div>

      {/* Expanded panel */}
      {open && (
        <div className="mt-3 flex gap-3">
          {/* Message history */}
          <div className="flex-1 max-h-32 overflow-y-auto rounded-lg border border-[var(--stroke)] bg-slate-50 p-3 text-xs flex flex-col gap-2">
            {messages.length === 0 ? (
              <p className="text-[var(--gray-text)]">Ask the AI to add, move, or edit cards.</p>
            ) : (
              messages.map((msg, i) => (
                <div key={i}>
                  <span className="font-semibold uppercase tracking-wider text-[10px] text-[var(--gray-text)]">
                    {msg.role}
                  </span>
                  <p className="mt-0.5">{msg.text}</p>
                </div>
              ))
            )}
          </div>
          {/* Input */}
          <div className="flex flex-col gap-2 w-72">
            {error && <p className="text-xs text-red-600">{error}</p>}
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
              rows={3}
              className="text-xs rounded-md border border-[var(--stroke)] px-3 py-2 resize-none outline-none focus:border-[var(--primary-blue)]"
              placeholder="Ask AI to update your board..."
            />
            <button
              onClick={sendMessage}
              disabled={isSending}
              className="text-xs font-semibold px-3 py-2 rounded-md text-white transition disabled:opacity-50"
              style={{ background: "var(--secondary-purple)" }}
            >
              {isSending ? "Thinking..." : "Send"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
