import { describe, expect, it } from 'vitest'
import { contentText, safeExternalHref } from './safeContent'

describe('safe content policy', () => {
  it('keeps model and corpus strings as plain text', () => {
    expect(contentText('<img src=x onerror=alert(1)>')).toBe('<img src=x onerror=alert(1)>')
  })

  it('allows only reviewed external URL schemes', () => {
    expect(safeExternalHref('https://example.test/evidence')).toBe('https://example.test/evidence')
    expect(safeExternalHref('mailto:security')).toBe('mailto:security')
    expect(safeExternalHref('javascript:alert(1)')).toBeNull()
    expect(safeExternalHref('data:text/html,<script>alert(1)</script>')).toBeNull()
    expect(safeExternalHref('/relative-path')).toBeNull()
  })
})
