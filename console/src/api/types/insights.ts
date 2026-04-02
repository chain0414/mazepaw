export interface DailyDigestItem {
  id: string;
  title: string;
  summary: string;
  source_agent: string;
  created_at: string;
  repo_scope: string[];
  sources: string[];
  metadata: Record<string, unknown>;
}

export interface ReviewQueueItem {
  id: string;
  title: string;
  summary: string;
  item_type: string;
  source_agent: string;
  status: string;
  created_at: string;
  updated_at: string;
  repo_scope: string[];
  action_payload: Record<string, unknown>;
  resolution_note: string;
}
