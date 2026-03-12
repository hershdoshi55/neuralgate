const PROXY_API_KEY = import.meta.env.VITE_PROXY_API_KEY ?? ''

export function apiFetch(input: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers)
  if (PROXY_API_KEY) headers.set('Authorization', `Bearer ${PROXY_API_KEY}`)
  return fetch(input, { ...init, headers })
}
