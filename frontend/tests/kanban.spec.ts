import { expect, test } from "@playwright/test";

const SEED_BOARD = {
  columns: [
    { id: "col-backlog", title: "Backlog", cardIds: ["card-1", "card-2"] },
    { id: "col-in-progress", title: "In Progress", cardIds: [] },
    { id: "col-review", title: "Review", cardIds: [] },
    { id: "col-done", title: "Done", cardIds: [] },
    { id: "col-blocked", title: "Blocked", cardIds: [] },
  ],
  cards: {
    "card-1": { id: "card-1", title: "Set up project", details: "Initialize files and repo." },
    "card-2": { id: "card-2", title: "Create baseline UI", details: "Add Kanban board components." },
  },
};

test.beforeEach(async ({ request }) => {
  await request.post("/api/kanban", {
    data: { user: "user", board: SEED_BOARD },
  });
});

test("loads the kanban board", async ({ page }) => {
  await page.goto("/");
  await page.waitForSelector('h1:has-text("Kanban Studio")', { timeout: 30000 });
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();
  await expect(page.locator('[data-testid^="column-"]')).toHaveCount(5);
});

test("adds a card to a column", async ({ page }) => {
  await page.goto("/");
  await page.waitForSelector('[data-testid^="column-"]', { timeout: 30000 });
  const firstColumn = page.locator('[data-testid^="column-"]').first();
  await firstColumn.getByRole("button", { name: /add a card/i }).click();
  await firstColumn.getByPlaceholder("Card title").fill("Playwright card");
  await firstColumn.getByPlaceholder("Details").fill("Added via e2e.");
  await firstColumn.getByRole("button", { name: /add card/i }).click();
  await expect(firstColumn.getByText("Playwright card")).toBeVisible();
});

test("moves a card between columns", async ({ page }) => {
  await page.goto("/");
  await page.waitForSelector('[data-testid="card-card-1"]', { timeout: 30000 });

  const moveRightInColumn = (columnId: string) =>
    page.getByTestId(columnId).getByTestId("card-card-1").getByRole("button", {
      name: /Move .* right/i,
    });

  await moveRightInColumn("column-col-backlog").click();
  await expect(page.getByTestId("column-col-in-progress").getByTestId("card-card-1")).toBeVisible();

  await moveRightInColumn("column-col-in-progress").click();
  await expect(page.getByTestId("column-col-review").getByTestId("card-card-1")).toBeVisible();

  await moveRightInColumn("column-col-review").click();
  await expect(page.getByTestId("column-col-done").getByTestId("card-card-1")).toBeVisible();
});
