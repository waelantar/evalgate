const ALLOWED_EXTERNAL_SCHEMES = new Set(['https:', 'mailto:'])

/**
 * The UI presents corpus and model values as React text nodes only. Do not add
 * HTML parsing or `dangerouslySetInnerHTML` to this boundary.
 */
export function contentText(value: string): string {
  return value
}

/**
 * EvalGate currently has no model- or corpus-authored outbound links. This
 * policy is the only permitted path if a reviewed UI later needs one.
 */
export function safeExternalHref(value: string): string | null {
  try {
    const url = new URL(value)
    return ALLOWED_EXTERNAL_SCHEMES.has(url.protocol) ? url.href : null
  } catch {
    return null
  }
}
