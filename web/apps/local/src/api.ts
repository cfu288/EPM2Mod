// The calls of `epm2mod serve` (src/epm2mod/serve.py). Each carries the token of the page's address (#token=...).

export interface Build {
  name: string
  what: string
  sha256: string | null
}

export interface Card {
  path: string
  name: string
  size: number
  free: number
  /** The card's name, size, free space and folder, for a list. */
  label: string
}

export interface Job {
  job: number
  lines: string[]
  done: boolean
  error: string | null
  sha256: string | null
  /** The card the files went to, or null for a zip. */
  card: string | null
  /** The files made, by their path on the card. */
  files: string[]
}

const token = () => new URLSearchParams(window.location.hash.slice(1)).get('token') ?? ''

async function call(path: string, init: RequestInit = {}): Promise<Response> {
  const response = await fetch(path, {
    ...init,
    headers: { 'X-EPM2-Token': token(), ...(init.body ? { 'Content-Type': 'application/json' } : {}) },
  })
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { error?: string } | null
    throw new Error(body?.error ?? `${String(response.status)} ${response.statusText}`)
  }
  return response
}

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  return (await (await call(path, init)).json()) as T
}

export const api = {
  build: () => json<Build>('/api/build'),
  cards: () => json<Card[]>('/api/cards'),
  make: (choices: string[], card: string | null) =>
    json<Job>('/api/make', { method: 'POST', body: JSON.stringify({ choices, card }) }),
  job: () => json<Job | null>('/api/job'),
  zip: async () => (await call('/api/zip')).blob(),
}
