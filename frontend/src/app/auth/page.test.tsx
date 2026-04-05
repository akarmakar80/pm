import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import AuthPage from "./page";

describe("AuthPage login gating", () => {
  beforeEach(() => {
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
