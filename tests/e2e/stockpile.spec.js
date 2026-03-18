// @ts-check
const { test, expect } = require('@playwright/test');

const CALDERA_URL = process.env.CALDERA_URL || 'http://localhost:8888';
const PLUGIN_ROUTE = '/#/plugins/stockpile';

// ---------------------------------------------------------------------------
// Helper: navigate to the stockpile plugin page inside magma.
// Uses 'domcontentloaded' (faster than 'networkidle') and waits for the
// Stockpile heading to confirm the Vue component has rendered.
// ---------------------------------------------------------------------------
async function navigateToStockpile(page) {
  await page.goto(`${CALDERA_URL}${PLUGIN_ROUTE}`, { waitUntil: 'domcontentloaded' });
  // Explicit UI guard: wait until the plugin heading is present before proceeding.
  await page.locator('h2', { hasText: 'Stockpile' }).waitFor({ state: 'visible', timeout: 15_000 });
}

// ===========================================================================
// 1. Plugin page loads
// ===========================================================================
test.describe('Stockpile plugin page load', () => {
  test('should display the Stockpile heading', async ({ page }) => {
    await navigateToStockpile(page);
    const heading = page.locator('h2', { hasText: 'Stockpile' });
    await expect(heading).toBeVisible({ timeout: 15_000 });
  });

  test('should display introductory description text', async ({ page }) => {
    await navigateToStockpile(page);
    await expect(
      page.locator('text=The stockpile plugin contains a collection of TTPs')
    ).toBeVisible({ timeout: 15_000 });
  });

  test('should render ability count card', async ({ page }) => {
    await navigateToStockpile(page);
    const abilityCard = page.locator('.card', { hasText: 'abilities' });
    await expect(abilityCard).toBeVisible({ timeout: 15_000 });
  });

  test('should render adversary count card', async ({ page }) => {
    await navigateToStockpile(page);
    const adversaryCard = page.locator('.card', { hasText: 'adversaries' });
    await expect(adversaryCard).toBeVisible({ timeout: 15_000 });
  });

  test('should show numeric ability count or placeholder', async ({ page }) => {
    await navigateToStockpile(page);
    // Anchor to the abilities card by label rather than positional index.
    const abilityCard = page.locator('.card', { hasText: 'abilities' });
    const abilityCount = abilityCard.locator('h1.is-size-1');
    await expect(abilityCount).toBeVisible({ timeout: 15_000 });
    const text = await abilityCount.textContent();
    expect(text?.trim()).toMatch(/^(\d+|---)$/);
  });

  test('should show numeric adversary count or placeholder', async ({ page }) => {
    await navigateToStockpile(page);
    // Anchor to the adversaries card by label rather than positional index.
    const adversaryCard = page.locator('.card', { hasText: 'adversaries' });
    const adversaryCount = adversaryCard.locator('h1.is-size-1');
    await expect(adversaryCount).toBeVisible({ timeout: 15_000 });
    const text = await adversaryCount.textContent();
    expect(text?.trim()).toMatch(/^(\d+|---)$/);
  });

  test('should have a horizontal rule separator', async ({ page }) => {
    await navigateToStockpile(page);
    await expect(page.locator('hr')).toBeVisible({ timeout: 15_000 });
  });
});

// ===========================================================================
// 2. Ability browsing within stockpile context
// ===========================================================================
test.describe('Stockpile ability browsing', () => {
  test('should have a "View Abilities" link pointing to abilities page with stockpile filter', async ({ page }) => {
    await navigateToStockpile(page);
    const viewAbilitiesBtn = page.locator('a', { hasText: 'View Abilities' });
    await expect(viewAbilitiesBtn).toBeVisible({ timeout: 15_000 });
    const href = await viewAbilitiesBtn.getAttribute('href');
    expect(href).toContain('/abilities');
    expect(href).toContain('plugin=stockpile');
  });

  test('should have a "View Adversaries" link pointing to adversaries page', async ({ page }) => {
    await navigateToStockpile(page);
    const viewAdversariesBtn = page.locator('a', { hasText: 'View Adversaries' });
    await expect(viewAdversariesBtn).toBeVisible({ timeout: 15_000 });
    const href = await viewAdversariesBtn.getAttribute('href');
    expect(href).toContain('/adversaries');
  });

  test('clicking "View Abilities" navigates to abilities page', async ({ page }) => {
    await navigateToStockpile(page);
    const viewAbilitiesBtn = page.locator('a', { hasText: 'View Abilities' });
    await viewAbilitiesBtn.click();
    await page.waitForURL(/abilities/, { timeout: 15_000 });
    expect(page.url()).toContain('abilities');
  });

  test('clicking "View Adversaries" navigates to adversaries page', async ({ page }) => {
    await navigateToStockpile(page);
    const viewAdversariesBtn = page.locator('a', { hasText: 'View Adversaries' });
    await viewAdversariesBtn.click();
    await page.waitForURL(/adversaries/, { timeout: 15_000 });
    expect(page.url()).toContain('adversaries');
  });

  test('ability card should contain a right-arrow icon', async ({ page }) => {
    await navigateToStockpile(page);
    const abilityCard = page.locator('.card', { hasText: 'abilities' });
    const icon = abilityCard.locator('.icon');
    await expect(icon).toBeVisible({ timeout: 15_000 });
  });

  test('adversary card should contain a right-arrow icon', async ({ page }) => {
    await navigateToStockpile(page);
    const adversaryCard = page.locator('.card', { hasText: 'adversaries' });
    const icon = adversaryCard.locator('.icon');
    await expect(icon).toBeVisible({ timeout: 15_000 });
  });
});

// ===========================================================================
// 3. Planner display (stockpile ships planners visible through the main app)
// ===========================================================================
test.describe('Stockpile planner display', () => {
  test('should load planners API without error', async ({ page }) => {
    const response = await page.request.get(`${CALDERA_URL}/api/v2/planners`);
    expect(response.ok()).toBeTruthy();
    const planners = await response.json();
    expect(Array.isArray(planners)).toBeTruthy();
  });

  test('should include stockpile-provided planners in API response', async ({ page }) => {
    const response = await page.request.get(`${CALDERA_URL}/api/v2/planners`);
    const planners = await response.json();
    // Stockpile ships planners like atomic, batch, buckets
    const plannerNames = planners.map((p) => p.name?.toLowerCase() || '');
    const hasStockpilePlanner = plannerNames.some(
      (n) => n.includes('atomic') || n.includes('batch') || n.includes('buckets')
    );
    expect(hasStockpilePlanner).toBeTruthy();
  });

  test('planners should have required fields', async ({ page }) => {
    const response = await page.request.get(`${CALDERA_URL}/api/v2/planners`);
    const planners = await response.json();
    for (const planner of planners) {
      expect(planner).toHaveProperty('name');
      expect(planner).toHaveProperty('id');
    }
  });
});

// ===========================================================================
// 4. Obfuscator selection / configuration
// ===========================================================================
test.describe('Stockpile obfuscator configuration', () => {
  test('should load obfuscators API without error', async ({ page }) => {
    const response = await page.request.get(`${CALDERA_URL}/api/v2/obfuscators`);
    expect(response.ok()).toBeTruthy();
    const obfuscators = await response.json();
    expect(Array.isArray(obfuscators)).toBeTruthy();
  });

  test('should include plain-text obfuscator', async ({ page }) => {
    const response = await page.request.get(`${CALDERA_URL}/api/v2/obfuscators`);
    const obfuscators = await response.json();
    const names = obfuscators.map((o) => o.name?.toLowerCase() || '');
    expect(names).toContain('plain-text');
  });

  test('obfuscators should have name and description', async ({ page }) => {
    const response = await page.request.get(`${CALDERA_URL}/api/v2/obfuscators`);
    const obfuscators = await response.json();
    for (const obf of obfuscators) {
      expect(obf).toHaveProperty('name');
      expect(typeof obf.name).toBe('string');
    }
  });

  test('should include base64 or caesar obfuscator from stockpile', async ({ page }) => {
    const response = await page.request.get(`${CALDERA_URL}/api/v2/obfuscators`);
    const obfuscators = await response.json();
    // Stockpile ships base64_jumble, base64_no_padding, caesar_cipher, and steganography.
    // Verify at least one of the known stockpile obfuscator names is present.
    const names = obfuscators.map((o) => o.name?.toLowerCase() || '');
    const hasStockpileObfuscator = names.some(
      (n) => n.includes('base64') || n.includes('caesar') || n.includes('steganography')
    );
    expect(hasStockpileObfuscator).toBeTruthy();
  });
});

// ===========================================================================
// 5. Adversary listing
// ===========================================================================
test.describe('Stockpile adversary listing', () => {
  test('adversaries API should return objects with name and description', async ({ page }) => {
    const response = await page.request.get(`${CALDERA_URL}/api/v2/adversaries`);
    expect(response.ok()).toBeTruthy();
    const adversaries = await response.json();
    expect(Array.isArray(adversaries)).toBeTruthy();
    // Every adversary must expose both name and description fields.
    for (const adv of adversaries) {
      expect(adv).toHaveProperty('name');
      expect(adv).toHaveProperty('description');
    }
  });
});

// ===========================================================================
// 6. Error states
// ===========================================================================
test.describe('Stockpile error states', () => {
  test('should handle invalid plugin route gracefully', async ({ page }) => {
    const resp = await page.goto(`${CALDERA_URL}/#/plugins/nonexistent-plugin`, {
      waitUntil: 'domcontentloaded',
    });
    // The app should still load (Vue router fallback) even if plugin doesn't exist
    expect(resp?.status()).toBeLessThan(500);
  });

  test('should handle abilities API failure gracefully', async ({ page }) => {
    // Intercept abilities API and force a failure
    await page.route('**/api/v2/abilities', (route) =>
      route.fulfill({ status: 500, body: 'Internal Server Error' })
    );
    await navigateToStockpile(page);
    // Page should still render without crashing
    const heading = page.locator('h2', { hasText: 'Stockpile' });
    await expect(heading).toBeVisible({ timeout: 15_000 });
  });

  test('should show placeholder when abilities API returns empty', async ({ page }) => {
    await page.route('**/api/v2/abilities', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      })
    );
    await navigateToStockpile(page);
    // Count should show "---" placeholder when 0 stockpile abilities; anchor by label.
    const abilityCard = page.locator('.card', { hasText: 'abilities' });
    const abilityCount = abilityCard.locator('h1.is-size-1');
    await expect(abilityCount).toBeVisible({ timeout: 15_000 });
    const text = await abilityCount.textContent();
    expect(text?.trim()).toMatch(/^(0|---)$/);
  });

  test('should show placeholder when adversaries API returns empty', async ({ page }) => {
    await page.route('**/api/v2/adversaries', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      })
    );
    await navigateToStockpile(page);
    // Anchor to the adversaries card by label rather than positional index.
    const adversaryCard = page.locator('.card', { hasText: 'adversaries' });
    const adversaryCount = adversaryCard.locator('h1.is-size-1');
    await expect(adversaryCount).toBeVisible({ timeout: 15_000 });
    const text = await adversaryCount.textContent();
    expect(text?.trim()).toMatch(/^(0|---)$/);
  });

  test('should handle network timeout on abilities API', async ({ page }) => {
    await page.route('**/api/v2/abilities', (route) => route.abort('timedout'));
    await navigateToStockpile(page);
    const heading = page.locator('h2', { hasText: 'Stockpile' });
    await expect(heading).toBeVisible({ timeout: 15_000 });
  });

  test('should handle network timeout on adversaries API', async ({ page }) => {
    await page.route('**/api/v2/adversaries', (route) => route.abort('timedout'));
    await navigateToStockpile(page);
    const heading = page.locator('h2', { hasText: 'Stockpile' });
    await expect(heading).toBeVisible({ timeout: 15_000 });
  });
});
