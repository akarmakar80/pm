const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();
  await page.goto('http://127.0.0.1:3000');
  await page.waitForSelector('[data-testid="card-card-1"]', { timeout: 30000 });
  const html = await page.locator('[data-testid="card-card-1"]').innerHTML();
  console.log('CARD1 HTML:', html);
  const labels = await page.locator('[data-testid="card-card-1"] button').allTextContents();
  console.log('BUTTON TEXTS:', labels);
  const aria = await page.locator('[data-testid="card-card-1"] button').evaluateAll((els) => els.map((el) => el.getAttribute('aria-label')));
  console.log('BUTTON ARIA LABELS:', aria);
  await browser.close();
})();