export type CredentialType = "git" | "social" | "deploy";

export interface CredentialProfile {
  id: string;
  type: CredentialType;
  provider: string;
  name: string;
  auth_method: string;
  secret_ref: string;
  metadata: Record<string, unknown>;
  acquisition_notes: string;
  git_user_name?: string;
  git_user_email?: string;
}

export interface CredentialListResponse {
  profiles: CredentialProfile[];
}

export interface CredentialCreateRequest {
  type: CredentialType;
  provider?: string;
  name?: string;
  auth_method?: string;
  secret_ref?: string;
  metadata?: Record<string, unknown>;
  acquisition_notes?: string;
  git_user_name?: string;
  git_user_email?: string;
}

export interface SSHKeyInfo {
  name: string;
  private_path: string;
  public_path: string;
  pub_content: string;
  comment: string;
  key_type: string;
}

export interface SSHTestResult {
  success: boolean;
  message: string;
  github_username: string | null;
}

export interface SSHConfigRead {
  content: string;
  exists: boolean;
}

export interface SSHConfigApplyResult {
  full_content: string;
}
