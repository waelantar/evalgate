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

test('inspects reviewed run and failed-case evidence without accessibility violations', async ({ page }) => {
  await routeResults(page, 'loaded')
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Evaluation results' })).toBeVisible()
  await expect(page.getByText('No semantic judge.')).toBeVisible()
  await expect(page.getByRole('heading', { name: /dev-01: What is the purpose/ })).toBeVisible()
  await expect(page.getByText('evidence-1')).toBeVisible()
  const results = await new AxeBuilder({ page }).analyze()
  expect(results.violations).toEqual([])
})

test('renders the reviewed-run empty state', async ({ page }) => {
  await routeResults(page, 'empty')
  await page.goto('/')
  await expect(page.getByText('No reviewed evaluation runs are available.')).toBeVisible()
})

test('renders a safe result error without server details', async ({ page }) => {
  await routeResults(page, 'error')
  await page.goto('/')
  await expect(page.getByRole('alert')).toContainText('could not be loaded')
  await expect(page.getByText('private dependency failure')).toHaveCount(0)
})
