# Frontend AGENTS guide

## Existing code overview

This frontend folder contains a working Next.js MVP Kanban demo app.

Key files:
- `src/app/page.tsx`: main page that displays the Kanban board.
- `src/components/KanbanBoard.tsx`: main board component.
- `src/components/KanbanColumn.tsx`: column rendering logic and drag/drop handlers.
- `src/components/KanbanCard.tsx`: card display and edit logic.
- `src/components/KanbanCardPreview.tsx`: preview states for drag-and-drop.
- `src/components/NewCardForm.tsx`: form to add cards.
- `src/lib/kanban.ts`: business logic helpers for card/column operations.

Existing tests:
- `src/components/KanbanBoard.test.tsx`
- `src/lib/kanban.test.ts`
- integration tests in `tests/kanban.spec.ts`

## Short-term goals for Part 1

1. Validate the plan in `docs/PLAN.md` with the user.
2. Improve the plan into an explicit checklist for the agent.
3. Create this `frontend/AGENTS.md` to capture current frontend behavior and tracking.

## Checklist (Part 1)

- [x] Confirm existing code and architecture.
- [x] Document frontend-specific state and API readiness.
- [x] Add success criteria for Part 1.

### Part 1 success criteria:
- Agent has an actionable project plan in `docs/PLAN.md` and `frontend/AGENTS.md`.
- User confirmed the plan before the next stage.
- Team can run frontend tests to validate the starting point.

## Proposed structured output format for AI interface (future)

- response: string (user-facing text)
- continue: boolean (whether to ask follow-up)
- action: object|null with fields:
  - type: `update_card`|`move_card`|`create_card`|`rename_column`|`none`
  - payload: object, optional specifics of the change.

