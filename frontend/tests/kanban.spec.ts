import { expect, test } from "@playwright/test";

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
  await expect(page.getByTestId("column-col-discovery").getByTestId("card-card-1")).toBeVisible();

  await moveRightInColumn("column-col-discovery").click();
  await expect(page.getByTestId("column-col-progress").getByTestId("card-card-1")).toBeVisible();

  await moveRightInColumn("column-col-progress").click();
  await expect(page.getByTestId("column-col-review").getByTestId("card-card-1")).toBeVisible();
});
