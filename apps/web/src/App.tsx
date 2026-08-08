import { useState } from 'react'

type HealthState = 'idle' | 'checking' | 'available' | 'unavailable'

const messages: Record<HealthState, string> = {
  idle: 'API status has not been checked.',
  checking: 'Checking the local API...',
  available: 'The local API is available.',
  unavailable: 'The local API is unavailable. Start it and try again.',
}

export function App() {
  const [health, setHealth] = useState<HealthState>('idle')

  async function checkApi() {
    setHealth('checking')
    try {
      const response = await fetch('/health/live', {
        headers: { Accept: 'application/json' },
      })
      setHealth(response.ok ? 'available' : 'unavailable')
    } catch {
      setHealth('unavailable')
    }
  }

  return (
    <main>
      <section className="hero" aria-labelledby="page-title">
        <p className="eyebrow">Engineering foundation</p>
        <h1 id="page-title">EvalGate</h1>
        <p className="summary">
          Evidence-driven change control for retrieval, grounding, and citations.
        </p>
      </section>

      <section className="status-card" aria-labelledby="foundation-status">
        <div>
          <p className="eyebrow">Current state</p>
          <h2 id="foundation-status">Foundation only</h2>
          <p>
            Product flows are planned and tracked in the production blueprint. This screen proves only
            the frontend and API foundation.
          </p>
        </div>

        <div className="health-check">
          <button type="button" onClick={() => void checkApi()} disabled={health === 'checking'}>
            {health === 'checking' ? 'Checking...' : 'Check local API'}
          </button>
          <p className={`health health--${health}`} role="status" aria-live="polite">
            {messages[health]}
          </p>
        </div>
      </section>
    </main>
  )
}
