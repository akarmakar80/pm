"use client";

import { useEffect, useState } from "react";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { KanbanColumn } from "@/components/KanbanColumn";
import { KanbanCardPreview } from "@/components/KanbanCardPreview";
import { AiChatWidget } from "@/components/AiChatWidget";
import { createId, moveCard, type BoardData } from "@/lib/kanban";

type KanbanBoardProps = {
  user?: string;
  onLogout?: () => void;
};

export const KanbanBoard = ({ user = "user", onLogout }: KanbanBoardProps) => {
  const [board, setBoard] = useState<BoardData | null>(null);
  const [activeCardId, setActiveCardId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } })
  );

  useEffect(() => {
    const loadBoard = async () => {
      setIsLoading(true);
      setError("");
      try {
        const res = await fetch(`/api/kanban?user=${encodeURIComponent(user)}`);
        if (!res.ok) throw new Error(`Unable to load board: ${res.status}`);
        setBoard(await res.json());
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setIsLoading(false);
      }
    };
    loadBoard();
  }, [user]);

  const saveBoard = async (updatedBoard: BoardData) => {
    try {
      const res = await fetch("/api/kanban", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user, board: updatedBoard }),
      });
      if (!res.ok) throw new Error(`Save failed: ${res.status}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const setAndSave = (updater: (prev: BoardData) => BoardData) => {
    setBoard((prev) => {
      if (!prev) return prev;
      const next = updater(prev);
      saveBoard(next);
      return next;
    });
  };

  const syncBoard = (nextBoard: BoardData) => setAndSave(() => nextBoard);

  const handleDragStart = (event: DragStartEvent) => setActiveCardId(event.active.id as string);

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveCardId(null);
    if (!over || active.id === over.id) return;
    setAndSave((prev) => ({
      ...prev,
      columns: moveCard(prev.columns, active.id as string, over.id as string),
    }));
  };

  const handleRenameColumn = (columnId: string, title: string) => {
    setAndSave((prev) => ({
      ...prev,
      columns: prev.columns.map((col) => col.id === columnId ? { ...col, title } : col),
    }));
  };

  const handleAddCard = (columnId: string, title: string, details: string) => {
    const id = createId("card");
    setAndSave((prev) => ({
      ...prev,
      cards: { ...prev.cards, [id]: { id, title, details } },
      columns: prev.columns.map((col) =>
        col.id === columnId ? { ...col, cardIds: [...col.cardIds, id] } : col
      ),
    }));
  };

  const handleDeleteCard = (columnId: string, cardId: string) => {
    setAndSave((prev) => ({
      ...prev,
      cards: Object.fromEntries(Object.entries(prev.cards).filter(([id]) => id !== cardId)),
      columns: prev.columns.map((col) =>
        col.id === columnId ? { ...col, cardIds: col.cardIds.filter((id) => id !== cardId) } : col
      ),
    }));
  };

  const moveCardToColumn = (cardId: string, fromColId: string, toColId: string) => {
    setAndSave((prev) => {
      const from = prev.columns.find((c) => c.id === fromColId);
      if (!from?.cardIds.includes(cardId) || fromColId === toColId) return prev;
      return {
        ...prev,
        columns: prev.columns.map((col) => {
          if (col.id === fromColId) return { ...col, cardIds: col.cardIds.filter((id) => id !== cardId) };
          if (col.id === toColId) return { ...col, cardIds: [...col.cardIds, cardId] };
          return col;
        }),
      };
    });
  };

  const handleMoveLeft = (columnId: string, cardId: string) => {
    if (!board) return;
    const idx = board.columns.findIndex((c) => c.id === columnId);
    if (idx > 0) moveCardToColumn(cardId, columnId, board.columns[idx - 1].id);
  };

  const handleMoveRight = (columnId: string, cardId: string) => {
    if (!board) return;
    const idx = board.columns.findIndex((c) => c.id === columnId);
    if (idx < board.columns.length - 1) moveCardToColumn(cardId, columnId, board.columns[idx + 1].id);
  };

  const activeCard = activeCardId ? board?.cards[activeCardId] ?? null : null;

  return (
    <div className="flex flex-col h-screen overflow-hidden" style={{ background: "var(--surface)" }}>
      {/* Top bar */}
      <header
        className="flex-none flex items-center justify-between px-6 h-14 border-b"
        style={{ background: "var(--navy-dark)", borderColor: "rgba(255,255,255,0.08)" }}
      >
        <div className="flex items-center gap-3">
          <span
            className="h-5 w-1 rounded-full"
            style={{ background: "var(--accent-yellow)" }}
          />
          <h1 className="font-display font-semibold text-white text-base tracking-wide">
            Kanban Studio
          </h1>
        </div>
        {onLogout && (
          <button
            onClick={onLogout}
            className="text-xs font-semibold px-3 py-1.5 rounded border text-white/70 border-white/20 hover:bg-white/10 transition"
          >
            Logout
          </button>
        )}
      </header>

      {/* Error banner */}
      {error && (
        <div className="flex-none px-6 py-2 text-sm text-red-700 bg-red-50 border-b border-red-200">
          {error}
        </div>
      )}

      {/* Board */}
      {isLoading ? (
        <div className="flex-1 flex items-center justify-center text-sm" style={{ color: "var(--gray-text)" }}>
          Loading board...
        </div>
      ) : !board ? (
        <div className="flex-1 flex items-center justify-center text-sm text-red-600">
          Failed to load board.
        </div>
      ) : (
        <DndContext
          sensors={sensors}
          collisionDetection={closestCorners}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <div className="flex-1 overflow-x-auto overflow-y-hidden">
            <div className="flex gap-4 h-full p-4 min-w-fit">
              {board.columns.map((column) => (
                <div key={column.id} className="w-72 flex-none flex flex-col h-full">
                  <KanbanColumn
                    column={column}
                    cards={column.cardIds.map((id) => board.cards[id]).filter(Boolean)}
                    onRename={handleRenameColumn}
                    onAddCard={handleAddCard}
                    onDeleteCard={handleDeleteCard}
                    onMoveLeft={handleMoveLeft}
                    onMoveRight={handleMoveRight}
                  />
                </div>
              ))}
            </div>
          </div>
          <DragOverlay>
            {activeCard && (
              <div className="w-72 opacity-90 shadow-2xl">
                <KanbanCardPreview card={activeCard} />
              </div>
            )}
          </DragOverlay>
        </DndContext>
      )}

      {/* AI chat */}
      {board && (
        <div
          className="flex-none border-t px-4 py-3"
          style={{ background: "white", borderColor: "var(--stroke)" }}
        >
          <AiChatWidget board={board} onBoardUpdate={syncBoard} user={user} />
        </div>
      )}
    </div>
  );
};
