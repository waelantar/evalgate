import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { App } from './App'

describe('foundation status', () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('does not claim planned product flows are implemented', () => {
    render(<App />)

    expect(screen.getByRole('heading', { name: 'Foundation only' })).toBeInTheDocument()
    expect(screen.getByText(/proves only the frontend and API foundation/i)).toBeInTheDocument()
  })

  it('reports a successful local API health check', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true }))
    render(<App />)

    fireEvent.click(screen.getByRole('button', { name: 'Check local API' }))

    expect(await screen.findByText('The local API is available.')).toBeInTheDocument()
  })
})
