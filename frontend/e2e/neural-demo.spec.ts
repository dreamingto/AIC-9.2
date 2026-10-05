import { expect, test } from '@playwright/test';

test('两个国内固定案例读取真实扫描并执行神经文本及区域检索', async ({ page, request }) => {
  const capability = await request.get('/api/v1/capabilities');
  const providers = (await capability.json()).providers;
  expect(providers.find((p: { provider: string }) => p.provider === 'bge_zh').available).toBeTruthy();
  expect(providers.find((p: { provider: string }) => p.provider === 'chinese_clip_image').available).toBeTruthy();
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/demo');
  await expect(page.getByRole('heading', { name: '国内古籍固定演示案例' })).toBeVisible();
  const loom = page.getByRole('article').filter({ hasText: '《耕织图》：织机与经线' });
  const water = page.getByRole('article').filter({ hasText: '《天工开物》：水碓与水磨' });
  for (const article of [loom, water]) {
    await expect(article.getByRole('img')).toHaveCount(2);
    for (const image of await article.getByRole('img').all()) {
      await expect.poll(() => image.evaluate((el: HTMLImageElement) => el.naturalWidth)).toBeGreaterThan(0);
    }
    for (const mode of ['text', 'region'] as const) {
      const pending = page.waitForResponse(response => response.url().endsWith('/search') && response.request().method() === 'POST');
      await article.getByRole('button', { name: mode === 'text' ? '运行文本检索' : '运行区域检索' }).click();
      const response = await pending;
      expect(response.ok(), await response.text()).toBeTruthy();
      const data = await response.json();
      expect(data.results.length).toBeGreaterThan(0);
      expect(data.model_versions.bge_zh.dimension).toBe(512);
      expect(data.model_versions.chinese_clip_image.dimension).toBe(512);
      expect(data.results.every((r: { verification_state: string; data_status: { human_reviewed: boolean } }) =>
        r.verification_state === 'pending' && r.data_status.human_reviewed === false)).toBeTruthy();
      await expect(page.getByRole('region', { name: '真实检索结果' })).toBeVisible();
    }
  }
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: 'test-results/playwright/neural-domestic-demo.png', fullPage: true });
  expect(errors).toEqual([]);
});
