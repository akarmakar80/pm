import clsx from "clsx";
import { useDroppable } from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";
import type { Card, Column } from "@/lib/kanban";
import { KanbanCard } from "@/components/KanbanCard";
import { NewCardForm } from "@/components/NewCardForm";

type KanbanColumnProps = {
  column: Column;
  cards: Card[];
  onRename: (columnId: string, title: string) => void;
  onAddCard: (columnId: string, title: string, details: string) => void;
  onDeleteCard: (columnId: string, cardId: string) => void;
  onMoveLeft?: (columnId: string, cardId: string) => void;
  onMoveRight?: (columnId: string, cardId: string) => void;
};

export const KanbanColumn = ({
  column,
  cards,
  onRename,
  onAddCard,
  onDeleteCard,
  onMoveLeft,
  onMoveRight,
}: KanbanColumnProps) => {
  const { setNodeRef, isOver } = useDroppable({ id: column.id });

  return (
    <div
      className={clsx(
        "flex flex-col h-full rounded-xl border bg-white transition",
        isOver ? "ring-2 ring-[var(--accent-yellow)]" : "border-[var(--stroke)]"
      )}
      style={{ boxShadow: "0 2px 8px rgba(3,33,71,0.06)" }}
      data-testid={`column-${column.id}`}
    >
      {/* Column header */}
      <div className="flex-none px-4 pt-4 pb-3 border-b border-[var(--stroke)]">
        <div className="h-1 w-8 rounded-full mb-3" style={{ background: "var(--accent-yellow)" }} />
        <div className="flex items-center justify-between gap-2">
          <input
            value={column.title}
            onChange={(e) => onRename(column.id, e.target.value)}
            className="flex-1 bg-transparent font-display font-semibold text-sm text-[var(--navy-dark)] outline-none min-w-0"
            aria-label="Column title"
          />
          <span className="flex-none text-xs font-semibold tabular-nums px-2 py-0.5 rounded-full bg-slate-100 text-[var(--gray-text)]">
            {cards.length}
          </span>
        </div>
      </div>

      {/* Cards — scrollable */}
      <div ref={setNodeRef} className="flex-1 overflow-y-auto px-3 py-3 flex flex-col gap-2 min-h-0">
        <SortableContext items={column.cardIds} strategy={verticalListSortingStrategy}>
          {cards.map((card) => (
            <KanbanCard
              key={card.id}
              card={card}
              onDelete={(cardId) => onDeleteCard(column.id, cardId)}
              onMoveLeft={(cardId) => onMoveLeft?.(column.id, cardId)}
              onMoveRight={(cardId) => onMoveRight?.(column.id, cardId)}
            />
          ))}
        </SortableContext>
        {cards.length === 0 && (
          <div className="flex-1 flex items-center justify-center rounded-lg border border-dashed border-[var(--stroke)] text-xs text-[var(--gray-text)] py-8">
            Drop here
          </div>
        )}
      </div>

      {/* Add card */}
      <div className="flex-none border-t border-[var(--stroke)] px-3 pt-3 pb-3">
        <NewCardForm onAdd={(title, details) => onAddCard(column.id, title, details)} />
      </div>
    </div>
  );
};
