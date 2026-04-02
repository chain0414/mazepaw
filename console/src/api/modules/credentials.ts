import { request } from "../request";
import type {
  CredentialCreateRequest,
  CredentialListResponse,
  CredentialProfile,
  SSHConfigApplyResult,
  SSHConfigRead,
  SSHKeyInfo,
  SSHTestResult,
} from "../types/credentials";

export const credentialsApi = {
  list: () => request<CredentialListResponse>("/credentials"),

  create: (body: CredentialCreateRequest) =>
    request<CredentialProfile>("/credentials", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  update: (id: string, body: CredentialProfile) =>
    request<CredentialProfile>(`/credentials/${encodeURIComponent(id)}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),

  delete: (id: string) =>
    request<{ success: boolean; id: string }>(
      `/credentials/${encodeURIComponent(id)}`,
      { method: "DELETE" },
    ),

  listSSHKeys: () => request<SSHKeyInfo[]>("/credentials/ssh-keys"),

  generateSSHKey: (body: {
    name: string;
    comment?: string;
    key_type?: string;
  }) =>
    request<SSHKeyInfo>("/credentials/ssh-keys/generate", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  testSSH: (body: { key_path: string; host?: string }) =>
    request<SSHTestResult>("/credentials/ssh-test", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  getSSHConfig: () => request<SSHConfigRead>("/credentials/ssh-config"),

  applySSHConfig: (body: {
    host_alias: string;
    hostname?: string;
    identity_file: string;
    user?: string;
  }) =>
    request<SSHConfigApplyResult>("/credentials/ssh-config/apply", {
      method: "POST",
      body: JSON.stringify(body),
    }),
};
