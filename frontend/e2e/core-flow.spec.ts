import {
  expect,
  request as createRequest,
  test,
  type APIRequestContext,
} from '@playwright/test';
import { fileURLToPath } from 'node:url';

const baseURL = process.env.E2E_BASE_URL ?? 'http://127.0.0.1';
const fixtureImage = fileURLToPath(
  new URL('../../backend/data/assets/fixture_v1/fig-bucket-wheel-01.png', import.meta.url),
);

type IngestionJob = {
  id: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  error_message: string | null;
};

type MinimalSearchResponse = {
  search_id: string;
  query_summary: { type: string; source_figure_id?: string };
  results: Array<{ candidate_id: string; figure_id: string }>;
};

let api: APIRequestContext;

async function ensureFixture(): Promise<void> {
  const created = await api.post('/api/v1/ingestion/jobs', {
    data: { manifest_name: 'jitu-fixture-v1.json', dry_run: false },
  });
  expect(created.status()).toBe(202);
  const initial = (await created.json()) as IngestionJob;

  for (let attempt = 0; attempt < 50; attempt += 1) {
    const response = await api.get(`/api/v1/ingestion/jobs/${initial.id}`);
    expect(response.ok()).toBeTruthy();
    const job = (await response.json()) as IngestionJob;
    if (job.status === 'completed') return;
    if (job.status === 'failed') {
      throw new Error(`Fixture ingestion failed: ${job.error_message ?? 'unknown error'}`);
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }

  throw new Error('Fixture ingestion did not complete within 5 seconds');
}

async function createTextSearch(): Promise<MinimalSearchResponse> {
  const response = await api.post('/api/v1/search/text', {
    data: {
      query: '提水',
      top_k: 10,
      filters: { book_ids: [], edition_ids: [] },
    },
  });
  expect(response.ok()).toBeTruthy();
  const search = (await response.json()) as MinimalSearchResponse;
  expect(search.results.length).toBeGreaterThan(0);
  return search;
}

test.describe.serial('机图索隐全栈演示闭环', () => {
  test.beforeAll(async () => {
    api = await createRequest.newContext({ baseURL });
    await ensureFixture();
  });

  test.afterAll(async () => {
    await api.dispose();
  });

  test('能力接口和来源页读取真实数据库', async ({ page }) => {
    const health = await api.get('/api/v1/health');
    expect(health.ok()).toBeTruthy();
    await expect(health.json()).resolves.toMatchObject({ status: 'ok', database: 'ok' });

    await page.goto('/sources');
    await expect(page.getByRole('heading', { name: /文献来源/ })).toBeVisible();
    await expect(page.getByText('农政全书（合成示例）').first()).toBeVisible();
    await expect(page.getByText('天工开物（合成示例）').first()).toBeVisible();
    await expect(page.getByText('纺织图谱（合成示例）').first()).toBeVisible();
  });

  test('文本检索进入比较页并提交人工核验', async ({ page }) => {
    await page.goto('/search');
    await page.getByLabel('检索词').fill('提水');
    const searchResponsePromise = page.waitForResponse(
      (response) => response.url().endsWith('/api/v1/search/text') && response.ok(),
    );
    await page.getByRole('button', { name: '搜索' }).click();
    await searchResponsePromise;

    await expect(page.getByText(/候选关联:/).first()).toBeVisible();
    await expect(page.getByText('图片受限').first()).toBeVisible();
    await page.getByRole('button', { name: /对照与核验/ }).first().click();
    await expect(page).toHaveURL(/\/compare\/[0-9a-f-]+$/);

    const verifyButton = page.getByRole('button', { name: '提交 worth_comparing' });
    await expect(verifyButton).toBeEnabled();
    const note = `playwright smoke ${Date.now()}`;
    await page.getByLabel(/核验备注/).fill(note);
    const verifyResponsePromise = page.waitForResponse(
      (response) => response.url().endsWith('/verify') && response.ok(),
    );
    await verifyButton.click();
    await verifyResponsePromise;
    await expect(page.getByText(/已更新核验状态为: worth_comparing/)).toBeVisible();
    await expect(page.getByText(/当前状态：/)).toContainText('worth_comparing');
  });

  test('图片与区域检索通过真实上传和裁剪接口', async ({ page }) => {
    const seedSearch = await createTextSearch();
    const sourceFigureId = seedSearch.results[0].figure_id;

    await page.goto('/search');
    await page.getByRole('tab', { name: '图片' }).click();
    await page.getByLabel(/上传检索图/).setInputFiles(fixtureImage);
    const imageResponsePromise = page.waitForResponse(
      (response) => response.url().endsWith('/api/v1/search/image') && response.ok(),
    );
    await page.getByRole('button', { name: '图片检索' }).click();
    await imageResponsePromise;
    await expect(page.getByText(/候选关联:/).first()).toBeVisible();

    await page.getByRole('tab', { name: '区域' }).click();
    await page.getByLabel('UUID').fill(sourceFigureId);
    await page.getByLabel('X').fill('0');
    await page.getByLabel('Y').fill('0');
    await page.getByLabel('Width').fill('0.5');
    await page.getByLabel('Height').fill('0.5');
    const regionResponsePromise = page.waitForResponse(
      (response) => response.url().endsWith('/api/v1/search/region') && response.ok(),
    );
    await page.getByRole('button', { name: '区域检索' }).click();
    const regionResponse = await regionResponsePromise;
    const regionSearch = (await regionResponse.json()) as MinimalSearchResponse;
    expect(regionSearch.query_summary).toMatchObject({
      type: 'region',
      source_figure_id: sourceFigureId,
    });
    expect(regionSearch.results.length).toBeGreaterThan(0);
    await expect(page.getByText(/候选关联:/).first()).toBeVisible();
  });
});
