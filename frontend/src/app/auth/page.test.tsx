import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import AuthPage from "./page";

const mockedBoard = {
  columns: [
    { id: "col-backlog", title: "Backlog", cardIds: [] },
    { id: "col-in-progress", title: "In Progress", cardIds: [] },
    { id: "col-review", title: "Review", cardIds: [] },
    { id: "col-done", title: "Done", cardIds: [] },
    { id: "col-blocked", title: "Blocked", cardIds: [] },
  ],
  cards: {},
};

describe("AuthPage login gating", () => {
  beforeEach(() => {
    vi.spyOn(global, "fetch").mockImplementation(async (input) => {
      const url = typeof input === "string" ? input : input?.toString();
      if (url?.startsWith("/api/kanban")) {
        return { ok: true, json: async () => mockedBoard } as any;
      }
      return { ok: false, status: 404, json: async () => ({}) } as any;
    });

    const storage: Record<string, string> = {};
    const mockLocalStorage = {
      getItem(key: string) {
        return Object.prototype.hasOwnProperty.call(storage, key) ? storage[key] : null;
      },
      setItem(key: string, value: string) {
        storage[key] = value;
      },
      removeItem(key: string) {
        delete storage[key];
      },
      clear() {
        Object.keys(storage).forEach((k) => delete storage[k]);
      },
    };

    Object.defineProperty(window, "localStorage", {
      value: mockLocalStorage,
      writable: true,
    });
  });

  it("requires login and then shows board with valid credentials", async () => {
    render(<AuthPage />);

    expect(screen.getByRole("heading", { name: /please sign in/i })).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText(/username/i), "user");
    await userEvent.type(screen.getByLabelText(/password/i), "password");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByRole("heading", { name: /kanban studio/i })).toBeInTheDocument();
    expect(window.localStorage.getItem("pm_logged_in")).toBe("true");

    await userEvent.click(screen.getByRole("button", { name: /logout/i }));
    expect(screen.getByRole("heading", { name: /please sign in/i })).toBeInTheDocument();
  });
});
