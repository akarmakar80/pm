import { beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { KanbanBoard } from "@/components/KanbanBoard";

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
      const payload = init.body ? JSON.parse(init.body.toString()) : {};
      return { ok: true, json: async () => ({ status: "ok", board: payload.board }) } as any;
    }

    if (url?.startsWith("/api/ai/kanban")) {
      return { ok: true, json: async () => ({ status: "ok", text_response: "done", board_update: null }) } as any;
    }

    if (url?.startsWith("/api/ai/ping")) {
      return { ok: true, json: async () => ({ status: "ok", value: 4 }) } as any;
    }

    return { ok: false, status: 404, json: async () => ({}) } as any;
  });
});

const getFirstColumn = async () => (await screen.findAllByTestId(/column-/i))[0];

describe("KanbanBoard", () => {
  it("renders five columns", async () => {
    render(<KanbanBoard />);
    const columns = await screen.findAllByTestId(/column-/i);
    expect(columns).toHaveLength(5);
  });

  it("renames a column", async () => {
    render(<KanbanBoard />);
    const column = await getFirstColumn();
    const input = within(column).getByLabelText("Column title");
    await userEvent.clear(input);
    await userEvent.type(input, "New Name");
    expect(input).toHaveValue("New Name");
  });

  it("adds and removes a card", async () => {
    render(<KanbanBoard />);
    const column = await getFirstColumn();
    const addButton = within(column).getByRole("button", {
      name: /add a card/i,
    });
    await userEvent.click(addButton);

    const titleInput = within(column).getByPlaceholderText(/card title/i);
    await userEvent.type(titleInput, "New card");
    const detailsInput = within(column).getByPlaceholderText(/details/i);
    await userEvent.type(detailsInput, "Notes");

    await userEvent.click(within(column).getByRole("button", { name: /add card/i }));

    expect(within(column).getByText("New card")).toBeInTheDocument();

    const deleteButton = within(column).getByRole("button", {
      name: /delete new card/i,
    });
    await userEvent.click(deleteButton);

    expect(within(column).queryByText("New card")).not.toBeInTheDocument();
  });
});
