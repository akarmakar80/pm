const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto('http://127.0.0.1:3000');
  await page.waitForLoadState('networkidle');
  const h1 = await page.textContent('h1').catch(() => 'notfound');
  console.log('h1', h1);
  const columns = await page.$$eval('[data-testid^="column-"]', els => els.length);
  console.log('col count', columns);
  await browser.close();
})();
