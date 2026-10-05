import { expect, test } from '@playwright/test';

test.describe('国内古籍 AI 辅助比赛演示', () => {
  test('真实语料筛选、原图和 AI 文本来源在页面中可见', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto('/search');
    await page.getByRole('combobox', { name: '检索数据' }).selectOption('ai_assisted_real_pilot');
    await page.getByLabel('检索词').fill('织机 经线');
    const responsePromise = page.waitForResponse(response =>
      response.url().endsWith('/api/v1/search/text') && response.request().method() === 'POST');
    await page.getByRole('button', { name: '搜索', exact: true }).click();
    const response = await responsePromise;
    expect(response.ok()).toBeTruthy();
    const payload = await response.json();
    expect(payload.results.length).toBeGreaterThan(0);
    expect(payload.results.every((r: { data_status: { dataset_kind: string } }) =>
      r.data_status.dataset_kind === 'ai_assisted_real_pilot')).toBeTruthy();
    await expect(page.getByText(/国内出版来源 · AI 辅助整理/).first()).toBeVisible();
    await expect(page.getByText('Wikimedia Commons / 中华再造善本 / 国家图书馆出版社').first()).toBeVisible();
    await page.getByRole('button', { name: '查看原图与文本 →' }).first().click();
    await expect(page).toHaveURL(/\/figures\//);
    await expect(page.getByText(/暂不人工审核 · 未评测/)).toBeVisible();
    await expect(page.getByText('AI 场景描述', { exact: false }).first()).toBeVisible();
    await expect(page.getByRole('link', { name: '来源目录' })).toHaveAttribute('href', /commons.wikimedia.org/);
    const image = page.getByRole('img', { name: 'Figure' });
    await expect(image).toBeVisible();
    await expect.poll(() => image.evaluate((element: HTMLImageElement) => element.naturalWidth)).toBeGreaterThan(0);
    await page.screenshot({ path: 'test-results/playwright/domestic-ai-figure.png', fullPage: true });
    expect(errors).toEqual([]);
  });

  test('真实扫描的图片及区域搜索通过 Nginx 调用后端并保持待核实', async ({ page, request }) => {
    const search = await request.post('/api/v1/search/text', { data: {
      query: '水磨', filters: { dataset_kinds: ['ai_assisted_real_pilot'] }, top_k: 1,
    } });
    expect(search.ok()).toBeTruthy();
    const candidate = (await search.json()).results[0];
    const detail = await request.get(`/api/v1/figures/${candidate.figure_id}`);
    expect(detail.ok()).toBeTruthy();
    const figure = await detail.json();
    const asset = await request.get(figure.asset.url);
    expect(asset.ok()).toBeTruthy();
    await page.goto('/search');
    await page.getByRole('combobox', { name: '检索数据' }).selectOption('ai_assisted_real_pilot');
    await page.getByRole('tab', { name: '图片', exact: true }).click();
    await page.getByLabel(/上传检索图/).setInputFiles({
      name: 'real-book.png', mimeType: 'image/png', buffer: await asset.body(),
    });
    const imageResponse = page.waitForResponse(response => response.url().endsWith('/api/v1/search/image'));
    await page.getByRole('button', { name: '图片检索', exact: true }).click();
    const uploadResponse = await imageResponse;
    expect(uploadResponse.ok(), `${uploadResponse.status()} ${await uploadResponse.text()}`).toBeTruthy();
    await expect(page.getByRole('button', { name: '查看原图与文本 →' }).first()).toBeVisible();
    await page.getByRole('tab', { name: '区域', exact: true }).click();
    await page.getByLabel('UUID', { exact: true }).fill(candidate.figure_id);
    await page.getByLabel('X', { exact: true }).fill(String(figure.bbox.x));
    await page.getByLabel('Y', { exact: true }).fill(String(figure.bbox.y));
    await page.getByLabel('Width', { exact: true }).fill(String(figure.bbox.width));
    await page.getByLabel('Height', { exact: true }).fill(String(figure.bbox.height));
    const regionResponse = page.waitForResponse(response => response.url().endsWith('/api/v1/search/region'));
    await page.getByRole('button', { name: '区域检索', exact: true }).click();
    const result = await regionResponse;
    expect(result.ok()).toBeTruthy();
    const payload = await result.json();
    expect(payload.results.length).toBeGreaterThan(0);
    expect(payload.results.every((r: { verification_state: string }) => r.verification_state === 'pending')).toBeTruthy();
    await page.getByRole('button', { name: '对照与核验 →' }).first().click();
    await expect(page.getByText(/暂不人工审核 · 未评测/)).toBeVisible();
    await expect(page.getByText(/归一化|坐标空间/).first()).toBeVisible();
  });
});
