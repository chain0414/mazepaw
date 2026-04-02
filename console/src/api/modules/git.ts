import { request } from "../request";

export interface GitCommitBody {
  files: string[];
  message: string;
  cwd: string;
  push?: boolean;
}

export interface GitCommitResult {
  success?: boolean;
  commit_hash?: string;
  message?: string;
  error?: string;
}

export const gitApi = {
  commit: (body: GitCommitBody) =>
    request<GitCommitResult>("/console/git/commit", {
      method: "POST",
      body: JSON.stringify(body),
    }),
};
