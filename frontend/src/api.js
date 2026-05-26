const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export async function search(query) {
  const resp = await fetch(`${BASE_URL}/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  })
  if (!resp.ok) {
    const data = await resp.json().catch(() => ({}))
    throw new Error(data.detail || `Request failed: ${resp.status}`)
  }
  return resp.json()
}
