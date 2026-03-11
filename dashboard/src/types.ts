export interface Summary {
  period_days: number
  total_requests: number
  total_cost_usd: number
  total_savings_usd: number
  savings_percent: number
  cache_hit_rate: number
  tokens_saved_by_cache: number
  avg_latency_ms: number
  p95_latency_ms: number
  by_tier: Record<string, { requests: number; cost_usd: number }>
  by_provider: Record<string, { requests: number; cost_usd: number }>
  by_model: Array<{ model: string; requests: number; cost_usd: number }>
}

export interface RoutingData {
  period_days: number
  total_requests: number
  failover_count: number
  failover_rate: number
  by_tier: Array<{ tier: string; requests: number; avg_complexity_score: number; percent: number }>
  by_model: Array<{ model: string; provider: string; tier: string | null; requests: number; avg_latency_ms: number }>
}

export interface DailySaving {
  date: string
  actual: number
  hypothetical: number
  saved: number
  requests: number
}

export interface SavingsData {
  period_days: number
  actual_cost_usd: number
  hypothetical_frontier_cost_usd: number
  total_savings_usd: number
  savings_percent: number
  daily_savings: DailySaving[]
}

export interface RecentRequest {
  request_id: string
  created_at: string
  requested_model: string
  selected_model: string
  selected_provider: string
  complexity_tier: string | null
  complexity_score: number | null
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  total_cost_usd: number
  cost_savings_usd: number
  cache_hit: boolean
  cache_similarity: number | null
  total_latency_ms: number
  failover_occurred: boolean
  finish_reason: string | null
  client_id: string | null
}
