import { getApiUrl, getApiToken } from "../config";

export interface LoginResponse {
  token: string;
  username: string;
  message?: string;
}

export interface AuthStatusResponse {
  enabled: boolean;
  has_users: boolean;
  feishu_login_available: boolean;
  password_login_allowed: boolean;
}

export interface VerifySessionResponse {
  valid: boolean;
  username: string;
  /** 飞书 OAuth 缓存的展示名；密码用户一般为用户名 */
  display_name?: string;
  /** 飞书头像 URL（由服务端在登录时缓存） */
  avatar_url?: string;
}

export const authApi = {
  login: async (username: string, password: string): Promise<LoginResponse> => {
    const res = await fetch(getApiUrl("/auth/login"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      const detail = err.detail;
      const msg =
        typeof detail === "string"
          ? detail
          : Array.isArray(detail)
            ? String(detail[0]?.msg ?? "Login failed")
            : "Login failed";
      throw new Error(msg);
    }
    return res.json();
  },

  register: async (
    username: string,
    password: string,
  ): Promise<LoginResponse> => {
    const res = await fetch(getApiUrl("/auth/register"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      const detail = err.detail;
      const msg =
        typeof detail === "string"
          ? detail
          : Array.isArray(detail)
            ? String(detail[0]?.msg ?? "Registration failed")
            : "Registration failed";
      throw new Error(msg);
    }
    return res.json();
  },

  getStatus: async (): Promise<AuthStatusResponse> => {
    const res = await fetch(getApiUrl("/auth/status"));
    if (!res.ok) throw new Error("Failed to check auth status");
    return res.json();
  },

  verifySession: async (): Promise<VerifySessionResponse> => {
    const headers: Record<string, string> = {};
    const token = getApiToken();
    if (token) headers.Authorization = `Bearer ${token}`;
    const res = await fetch(getApiUrl("/auth/verify"), { headers });
    if (res.status === 401) return { valid: false, username: "" };
    if (!res.ok) return { valid: false, username: "" };
    return res.json();
  },
};
