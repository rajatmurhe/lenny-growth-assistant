import { Session, HealthStatus, Provider, SSEEvent } from './types';

export const API_BASE = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000';

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: { message: res.statusText } }));
    throw new Error(err?.error?.message || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  // Sessions
  createSession: (provider = 'ollama') =>
    apiFetch<Session>('/sessions', {
      method: 'POST',
      body: JSON.stringify({ provider }),
    }),

  listSessions: () => apiFetch<Session[]>('/sessions'),

  getSession: (id: string) => apiFetch<Session>(`/sessions/${id}`),

  updateProvider: (sessionId: string, provider: string) =>
    apiFetch<{ provider: string; model: string }>(`/sessions/${sessionId}/provider`, {
      method: 'POST',
      body: JSON.stringify({ provider }),
    }),

  // Config
  getProviders: () =>
    apiFetch<{ providers: Provider[]; active: string }>('/config/providers'),

  // Health
  getHealth: () => apiFetch<HealthStatus>('/health/ready'),

  // Artifacts
  getArtifact: (id: string) =>
    apiFetch<{
      id: string;
      title: string;
      content: string;
      sanitized_content: string;
      type: string;
      version: number;
    }>(`/artifacts/${id}`),
};

/**
 * Stream a message via SSE (POST request + ReadableStream parsing).
 * Uses fetch instead of EventSource to support POST body.
 *
 * Returns a cancel function.
 */
export function streamMessage(
  sessionId: string,
  content: string,
  onEvent: (event: SSEEvent) => void,
  onDone: () => void,
  onError: (err: string) => void
): () => void {
  const controller = new AbortController();

  (async () => {
    try {
      const res = await fetch(`${API_BASE}/sessions/${sessionId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
        signal: controller.signal,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ error: { message: res.statusText } }));
        onError(err?.error?.message || `HTTP ${res.status}`);
        return;
      }

      const reader = res.body?.getReader();
      if (!reader) { onError('No response body'); return; }

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const event = JSON.parse(line.slice(6)) as SSEEvent;
              onEvent(event);
              if (event.type === 'done') { onDone(); return; }
            } catch {
              // Ignore malformed lines
            }
          }
        }
      }
      onDone();
    } catch (err: unknown) {
      if ((err as Error)?.name !== 'AbortError') {
        onError((err as Error)?.message || 'Stream error');
      }
    }
  })();

  return () => controller.abort();
}
