import { beforeEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import Home from "./page";

const mockedBoard = {
  columns: [
    { id: "col-backlog", title: "Backlog", cardIds: ["card-1"] },
    { id: "col-in-progress", title: "In Progress", cardIds: [] },
    { id: "col-review", title: "Review", cardIds: [] },
    { id: "col-done", title: "Done", cardIds: [] },
    { id: "col-blocked", title: "Blocked", cardIds: [] },
  ],
  cards: {
    "card-1": { id: "card-1", title: "Task", details: "Test task" },
  },
};

beforeEach(() => {
  vi.spyOn(global, "fetch").mockImplementation(async (input, init) => {
    const url = typeof input === "string" ? input : input?.toString();
    if (url?.startsWith("/api/kanban") && (!init || init.method === "GET")) {
      return { ok: true, json: async () => mockedBoard } as any;
    }
    if (url?.startsWith("/api/kanban") && init?.method === "POST") {
      return { ok: true, json: async () => ({ status: "ok", board: mockedBoard }) } as any;
    }
    if (url?.startsWith("/api/ai/kanban")) {
      return { ok: true, json: async () => ({ status: "ok", text_response: "ok", board_update: null }) } as any;
    }
    if (url?.startsWith("/api/ai/ping")) {
      return { ok: true, json: async () => ({ status: "ok", value: 4 }) } as any;
    }
    return { ok: false, status: 404, json: async () => ({}) } as any;
  });
});

describe("Home board view", () => {
  it("renders the Kanban board", async () => {
    render(<Home />);
    expect(await screen.findByRole("heading", { name: /kanban studio/i })).toBeInTheDocument();
    expect((await screen.findAllByTestId(/column-col-/i)).length).toBe(5);
  });
});
