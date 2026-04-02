// Multi-agent management types

export type AgentTemplateId = "general" | "developer" | "oss_researcher";

export interface AgentSummary {
  id: string;
  name: string;
  description: string;
  workspace_dir: string;
  module_id: string;
  template_id: string;
  repo_count: number;
}

export interface RepoAssetRef {
  id: string;
  name: string;
  local_path: string;
  remote_url?: string;
}

export interface IntegrationRef {
  id: string;
  kind: "github" | "chainos";
  name: string;
  config?: Record<string, unknown>;
}

export interface OutputPrefsConfig {
  inbox_enabled: boolean;
  summary_to_chat: boolean;
  digest_enabled: boolean;
  approvals_enabled: boolean;
}

export interface AgentListResponse {
  agents: AgentSummary[];
}

export interface AgentProfileConfig {
  id: string;
  name: string;
  description?: string;
  workspace_dir?: string;
  channels?: unknown;
  mcp?: unknown;
  heartbeat?: unknown;
  running?: unknown;
  llm_routing?: unknown;
  system_prompt_files?: string[];
  tools?: unknown;
  security?: unknown;
  module_id?: string;
  template_id?: AgentTemplateId;
  repo_assets?: RepoAssetRef[];
  integrations?: IntegrationRef[];
  output_prefs?: OutputPrefsConfig;
  git_credential_id?: string;
}

export interface CreateAgentRequest {
  name: string;
  description?: string;
  workspace_dir?: string;
  language?: string;
  module_id?: string;
  template_id?: AgentTemplateId;
  repo_assets?: RepoAssetRef[];
  integrations?: IntegrationRef[];
  output_prefs?: OutputPrefsConfig;
  git_credential_id?: string;
}

export interface AgentProfileRef {
  id: string;
  workspace_dir: string;
}

/** Optional ``git ls-remote`` probe per bound repo (see GET /agents/{id}/repo-connectivity). */
export interface RepoConnectivityEntry {
  repo_id: string;
  local_path: string;
  reachable: boolean | null;
  message: string;
}
