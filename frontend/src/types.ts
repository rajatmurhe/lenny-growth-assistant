export interface Session {
  id: string;
  title: string | null;
  provider: 'ollama' | 'anthropic';
  model: string;
  created_at: string;
  updated_at: string;
  messages?: Message[];
}

export interface Message {
  id: string;
  session_id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  skill_used?: string;
  latency_ms?: number;
  created_at: string;
}

export interface StreamingMessage {
  role: 'assistant';
  content: string;
  state?: 'streaming' | 'insufficient_evidence' | 'error';
  citations?: Citation[];
  closest_episodes?: string[];
  validation?: {
    passed: boolean;
    word_count: number;
    failures: string[];
  };
  latency_ms?: number;
}

export interface Citation {
  ordinal: number;
  chunk_id: string;
  episode_slug: string;
  episode_title: string;
  guest?: string;
  post_url?: string;
  text_snippet: string;
  rrf_score: number;
}

export interface Provider {
  name: string;
  available: boolean;
  reason?: string;
  models: { chat: string; embed?: string };
}

export interface HealthStatus {
  status: 'ready' | 'degraded' | 'not_ready';
  checks: Record<string, {
    status: string;
    latency_ms?: number;
    chunk_count?: number;
    model?: string;
    model_present?: boolean;
  }>;
}

export type SSEEvent =
  | { type: 'token'; content: string }
  | { type: 'citations'; citations: Citation[] }
  | { type: 'insufficient_evidence'; message?: string; closest_episodes?: string[] }
  | { type: 'repair_start'; failures: string[] }
  | { type: 'validation'; passed: boolean; word_count: number; failures: string[] }
  | { type: 'artifact'; artifact_id: string; title: string }
  | { type: 'error'; message: string; code?: string }
  | { type: 'done'; latency_ms?: number }
  | { type: string; [key: string]: unknown };
