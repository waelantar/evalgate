import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'

const run = {
  run_key: 'candidate-run',
  mode: 'retrieval',
  status: 'completed',
  code_sha: 'a'.repeat(40),
  artifact_sha256: 'b'.repeat(64),
}

async function routeResults(page: Page, state: 'loaded' | 'empty' | 'error'): Promise<void> {
  await page.route('**/api/v1/inspection-catalog', async (route) => {
    await route.fulfill({ json: { items: [] } })
  })
  await page.route('**/api/v1/evaluation-runs**', async (route) => {
    if (state === 'error') {
      await route.fulfill({ status: 503, json: { detail: 'private dependency failure' } })
      return
    }
    const url = new URL(route.request().url())
    if (url.pathname === '/api/v1/evaluation-runs') {
      await route.fulfill({ json: { items: state === 'empty' ? [] : [run], next_cursor: null } })
      return
    }
    if (url.pathname.endsWith('/cases')) {
      await route.fulfill({
        json: {
          items: [{ case_id: 'dev-01', split: 'development', question: 'What is the purpose?', answerable: true, status: 'failed', retrieved_evidence_ids: [], relevant_evidence_ids: ['evidence-1'], metric_values: { retrieval_hit: 0 } }],
          next_cursor: null,
        },
      })
      return
    }
    await route.fulfill({
      json: {
        ...run,
        versions: { index_key: 'reviewed-index', dataset_manifest_sha256: 'c'.repeat(64), corpus_manifest_sha256: 'd'.repeat(64), policy_version: 'hybrid-rrf-v1' },
        environment: { os: 'test' },
        metrics: { case_count: 36, mrr: 0.8 },
        limitations: ['No semantic judge.'],
        review: { decision: 'approved' },
        comparison_run_key: null,
        metric_deltas: null,
      },
    })
  })
}

function streamFrame(type: string, sequence: number, value: Record<string, unknown>): string {
  return `event: ${type}\nid: ${sequence}\ndata: ${JSON.stringify({ schema_version: '1.0', request_id: 'req-1', sequence, type, ...value })}\n\n`
}

async function routeAnswerAndEvidence(page: Page): Promise<void> {
  await page.route('**/api/v1/inspection-catalog', async (route) => {
    await route.fulfill({ json: { items: [{ index_version: 'fixture-v1', index_key: 'fixture-index', corpus_key: 'fixture-corpus', corpus_version: '1.0.0', label: 'Fixture corpus · 1.0.0' }] } })
  })
  await page.route('**/api/v1/ask', async (route) => {
    await route.fulfill({
      contentType: 'text/event-stream',
      body: [
        streamFrame('answer.started', 1, { prompt_policy: { id: 'policy', version: '1', sha256: 'hash' } }),
        streamFrame('retrieval.completed', 2, { index_version: 'fixture-v1', corpus_version: 'fixture-c1', evidence_ids: ['ev-1'] }),
        streamFrame('answer.delta', 3, { text: '<img src=x onerror=alert(1)>' }),
        streamFrame('citations.completed', 4, { citations: [{ evidence_id: 'ev-1', title: 'javascript:alert(1)', section_key: 'intro' }] }),
        streamFrame('answer.completed', 5, { status: 'answered', provider: { mode: 'fixture', name: 'fixture', revision: '1' } }),
      ].join(''),
    })
  })
  await page.route('**/api/v1/search**', async (route) => {
    await route.fulfill({
      json: { results: [{ rank: 1, evidence_id: 'ev-1', document_id: 'doc-1', source_key: 'fixture', title: 'javascript:alert(1)', license_id: 'internal', provenance: 'fixture', section_key: 'intro', source_start: 0, source_end: 10, content: '<img src=x onerror=alert(1)>', content_sha256: 'hash', lexical_rank: 1, vector_rank: null, rrf_score: 1 }] },
    })
  })
}

test('inspects reviewed run and failed-case evidence without accessibility violations', async ({ page }) => {
  await routeResults(page, 'loaded')
  await page.goto('/evaluations')
  await expect(page.getByRole('heading', { name: 'Evaluation results' })).toBeVisible()
  await expect(page.getByText('No semantic judge.')).toBeVisible()
  await expect(page.getByRole('heading', { name: /dev-01: What is the purpose/ })).toBeVisible()
  await page.getByText('Technical evidence IDs').click()
  await expect(page.getByText('evidence-1')).toBeVisible()
  const results = await new AxeBuilder({ page }).analyze()
  expect(results.violations).toEqual([])
})

test('renders the reviewed-run empty state', async ({ page }) => {
  await routeResults(page, 'empty')
  await page.goto('/evaluations')
  await expect(page.getByText('No reviewed evaluation runs are available.')).toBeVisible()
})

test('renders a safe result error without server details', async ({ page }) => {
  await routeResults(page, 'error')
  await page.goto('/evaluations')
  await expect(page.getByRole('alert')).toContainText('could not be loaded')
  await expect(page.getByText('private dependency failure')).toHaveCount(0)
})

test('keeps unsafe answer content inert and moves keyboard focus to cited evidence', async ({ page }) => {
  await routeResults(page, 'empty')
  await routeAnswerAndEvidence(page)
  await page.goto('/')
  await page.getByRole('button', { name: 'Inspect an answer' }).click()
  await expect(page.getByLabel('Evidence source')).toBeVisible()
  await page.getByLabel('Your question').fill('How?')
  await page.getByRole('button', { name: 'Inspect answer' }).focus()
  await page.keyboard.press('Enter')

  const citation = page.getByRole('button', { name: /javascript:alert/ })
  await expect(citation).toBeVisible()
  await expect(page.locator('img')).toHaveCount(0)
  await expect(page.locator('a[href^="javascript:"]')).toHaveCount(0)
  await citation.focus()
  await page.keyboard.press('Enter')
  await expect(page.locator('#evidence-ev-1')).toBeFocused()
})

test('reflows every primary route at 320 CSS pixels with reduced motion requested', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.setViewportSize({ width: 320, height: 720 })
  await routeResults(page, 'empty')
  await routeAnswerAndEvidence(page)

  for (const path of ['/', '/inspect', '/data', '/evaluations', '/showcase', '/system-evidence']) {
    await page.goto(path)
    const viewport = await page.evaluate<{ viewportWidth: number; scrollWidth: number }>(
      '({ viewportWidth: window.innerWidth, scrollWidth: document.documentElement.scrollWidth })',
    )
    expect(viewport.scrollWidth, `${path} must not create page-level horizontal scrolling`).toBeLessThanOrEqual(viewport.viewportWidth)
  }

  await page.goto('/')
  await page.getByRole('button', { name: 'Inspect an answer' }).click()
  await expect(page.getByLabel('Evidence source')).toBeVisible()
  await page.getByLabel('Your question').fill('How?')
  await page.getByRole('button', { name: 'Inspect answer' }).click()
  await page.getByRole('button', { name: /javascript:alert/ }).click()
  await expect(page.locator('#evidence-ev-1')).toBeFocused()
  const results = await new AxeBuilder({ page }).analyze()
  expect(results.violations).toEqual([])
})

test('turns a blocked request into a finite, retryable timeout state', async ({ page }) => {
  test.setTimeout(45_000)
  await routeResults(page, 'empty')
  await routeAnswerAndEvidence(page)
  await page.route('**/api/v1/ask', async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 35_000))
    await route.abort('timedout').catch(() => undefined)
  })
  await page.goto('/')
  await page.getByRole('button', { name: 'Inspect an answer' }).click()
  await expect(page.getByLabel('Evidence source')).toBeVisible()
  await page.getByLabel('Your question').fill('How?')
  await page.getByRole('button', { name: 'Inspect answer' }).click()
  const alert = page.getByRole('alert')
  await expect(alert).toContainText('The request took too long', { timeout: 40_000 })
  await expect(alert).toContainText('client.timeout')
  await expect(page.getByRole('status')).toContainText('Failed')
  await expect(page.getByRole('button', { name: 'Try again' })).toBeEnabled()
})

test('uses a collapsible primary menu at phone width', async ({ page }) => {
  await routeResults(page, 'empty')
  await routeAnswerAndEvidence(page)
  await page.setViewportSize({ width: 320, height: 720 })
  await page.goto('/')
  const navigation = page.getByRole('navigation', { name: 'Primary navigation' })
  const menu = page.getByRole('button', { name: 'Menu' })
  await expect(menu).toHaveAttribute('aria-expanded', 'false')
  await expect(navigation).not.toBeVisible()
  await menu.click()
  await expect(menu).toHaveAttribute('aria-expanded', 'true')
  await expect(navigation).toBeVisible()
  await navigation.getByRole('link', { name: 'Inspect' }).click()
  await expect(menu).toHaveAttribute('aria-expanded', 'false')
  await expect(page.getByRole('heading', { name: 'Trace an answer to its evidence.' })).toBeVisible()
})

test('persists dark mode and keeps future data lanes non-interactive', async ({ page }) => {
  await routeResults(page, 'empty')
  await routeAnswerAndEvidence(page)
  await page.goto('/')
  await page.getByRole('button', { name: 'Switch to night mode' }).click()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  await page.reload()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  await page.getByRole('link', { name: 'Bring data' }).click()
  await expect(page.getByRole('heading', { name: 'How a real user changes the source material.' })).toBeVisible()
  await expect(page.getByText('Self-serve browser upload')).toBeVisible()
  await expect(page.getByText('Account workspace')).toBeVisible()
  await expect(page.getByText('Hosted private storage')).toBeVisible()
  await expect(page.locator('input[type="file"]')).toHaveCount(0)
  await expect(page.getByRole('button', { name: /upload/i })).toHaveCount(0)
  const results = await new AxeBuilder({ page }).analyze()
  expect(results.violations).toEqual([])
})