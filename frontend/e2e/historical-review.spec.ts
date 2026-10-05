import { test, expect } from '@playwright/test';
import { existsSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const reviewPath = resolve('../backend/data/real_pilot/model_review_queue.html');
const source = 'commons-najda-tiangong-kaiwu-2';

test.describe('Local historical OCR review', () => {
  test.skip(!existsSync(reviewPath), 'Generate the local OCR review artifact first.');

  test('core scope preserves all candidates and completeness requires every text item', async ({ page }) => {
    await page.goto(pathToFileURL(reviewPath).href);
    await expect(page.locator('#scope-filter')).toHaveValue('core');
    await expect(page.locator('#page option')).toHaveCount(6);
    await page.locator('#page').selectOption(`${source}-p0022`);
    await page.locator('#reviewer').fill('test-only-inventory-reviewer');
    await page.locator('#inventory-confirmed').click();
    await expect(page.locator('#inventory-confirmed')).not.toBeChecked();
    await expect(page.locator('#message')).toContainText('完整性确认前');
    await page.locator('#filter').selectOption('all');
    const ids = await page.locator('#list button').evaluateAll(buttons =>
      buttons.map(button => button.getAttribute('data-id')!).filter(id => /-b\d{3}$|-title$/.test(id)),
    );
    expect(ids).toHaveLength(5);
    for (const id of ids) {
      await page.locator(`#list button[data-id="${id}"]`).click();
      await page.locator('#corrected').fill('测试校订');
      await page.locator('#confirmed').check();
      await page.locator('#save').click();
    }
    await page.locator('#page-confirmed').check();
    await page.locator('#inventory-confirmed').check();
    await expect(page.locator('#inventory-confirmed')).toBeChecked();
    const pending = page.waitForEvent('download');
    await page.locator('#export').click();
    const download = await pending;
    const payload = JSON.parse(await readFile((await download.path())!, 'utf8'));
    expect(payload.page_inventory_reviews).toHaveLength(1);
    expect(payload.page_inventory_reviews[0]).toMatchObject({
      page_id: `${source}-p0022`, text_complete: true, captions_complete: true,
      confirmed: true, reviewer: 'test-only-inventory-reviewer',
    });
    expect(payload.page_inventory_reviews[0].caption_ids).toContain(`${source}-p0022-f01-title`);
    await page.locator('#corrected').fill('测试改动撤销确认');
    await expect(page.locator('#inventory-confirmed')).not.toBeChecked();
    await expect(page.locator('#page-confirmed')).not.toBeChecked();
    await page.locator('#scope-filter').selectOption('all');
    // The empty cover has no queue items; 27 pages remain selectable.
    await expect(page.locator('#page option')).toHaveCount(27);
    await page.locator('#scope-filter').selectOption('core');
    await expect(page.locator('#corrected')).toHaveValue('测试改动撤销确认');
  });

  test('desktop images, full-page overlay, and deferred queue are accessible', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(pathToFileURL(reviewPath).href);
    await expect(page.getByRole('heading', { name: '机图索隐 · 古籍复核' })).toBeVisible();
    await expect(page.locator('.crop')).toHaveJSProperty('complete', true);
    expect(await page.locator('.crop').evaluate((img: HTMLImageElement) => img.naturalWidth)).toBeGreaterThan(0);
    await expect(page.locator('#page-image')).toHaveJSProperty('complete', true);
    expect(await page.locator('#overlay').evaluate((canvas: HTMLCanvasElement) => canvas.width)).toBeGreaterThan(0);
    await page.locator('#filter').selectOption('all');
    await page.locator('#scope-filter').selectOption('all');
    await page.locator('#page').selectOption(`${source}-p0002`);
    expect(await page.locator('#list button').count()).toBe(12);
    await page.screenshot({ path: 'test-results/historical-review-desktop.png', fullPage: true });
    expect(errors).toEqual([]);
  });

  test('missing caption export contains the actual confirmation and source hashes', async ({ page }) => {
    await page.goto(pathToFileURL(reviewPath).href);
    await page.locator('#page').selectOption(`${source}-p0022`);
    await page.locator(`#list button[data-id="${source}-p0022-f01-title"]`).click();
    await page.locator('#use').click();
    await expect(page.locator('#corrected')).toHaveValue('趕綿');
    await page.locator('#confirmed').check();
    await page.locator('#save').click();
    await expect(page.locator('#message')).toContainText('填写复核人');
    await page.locator('#reviewer').fill('browser-test-reviewer');
    await page.locator('#confirmed').check();
    await page.locator('#save').click();
    const pending = page.waitForEvent('download');
    await page.locator('#export').click();
    const download = await pending;
    const downloadPath = await download.path();
    expect(downloadPath).not.toBeNull();
    const payload = JSON.parse(await readFile(downloadPath!, 'utf8'));
    expect(payload.source_candidate_sha256).toMatch(/^[a-f0-9]{64}$/);
    expect(payload.input_hashes.label_sha256).toMatch(/^[a-f0-9]{64}$/);
    expect(payload.records).toHaveLength(1);
    expect(payload.records[0]).toMatchObject({
      box_or_figure_id: `${source}-p0022-f01-title`, corrected_text: '趕綿',
      kind: 'caption', category: 'caption', role: 'figure_title',
      reviewer: 'browser-test-reviewer', confirmed: true,
      verification_state: 'verified', evidence: 'scan_level_human_review',
    });
    expect(Number.isNaN(Date.parse(payload.records[0].reviewed_at))).toBe(false);
    await page.locator('#corrected').fill('待重新确认');
    await page.locator('#export').click();
    await expect(page.locator('#message')).toContainText('没有已保存并确认');
  });

  test('mobile layout, coordinate rejection, and draft navigation', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(pathToFileURL(reviewPath).href);
    await page.locator('#scope-filter').selectOption('all');
    await page.locator('#page').selectOption(`${source}-p0002`);
    await page.locator('#corrected').fill('测试草稿');
    await page.locator('#next').click();
    await page.locator('#prev').click();
    await expect(page.locator('#corrected')).toHaveValue('测试草稿');
    await page.locator('#bbox-width').fill('2');
    await page.locator('#save').click();
    await expect(page.locator('#message')).toContainText('页内归一化');
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await page.screenshot({ path: 'test-results/historical-review-mobile.png', fullPage: true });
  });
});
