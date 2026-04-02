import { ToolCall } from "@agentscope-ai/chat";
import {
  Button,
  Card,
  Checkbox,
  Collapse,
  Input,
  Modal,
  Space,
  Spin,
  Tag,
  Typography,
  message as antdMessage,
} from "antd";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { gitApi } from "../../../../api/modules/git";
import { DiffViewer } from "./DiffViewer";
import styles from "./index.module.less";

type ToolRenderData = {
  content?: Array<{
    data: {
      name?: string;
      server_label?: string;
      arguments?: unknown;
      output?: unknown;
    };
  }>;
  status?: string;
};

interface GitFileEntry {
  path: string;
  status: string;
  additions: number;
  deletions: number;
  diff: string;
}

interface GitProposePayload {
  schema?: string;
  repo_path?: string;
  summary?: string;
  files?: GitFileEntry[];
  total_additions?: number;
  total_deletions?: number;
  error?: string;
}

function parseGitProposeOutput(raw: unknown): GitProposePayload | null {
  if (raw == null) return null;
  let value: unknown = raw;
  if (typeof value === "string") {
    const text = value;
    try {
      value = JSON.parse(text);
    } catch {
      try {
        value = JSON.parse(JSON.parse(text) as string);
      } catch {
        return null;
      }
    }
  }
  if (typeof value === "object" && value !== null && !Array.isArray(value)) {
    return value as GitProposePayload;
  }
  return null;
}

export default function GitCommitCard(props: { data: ToolRenderData }) {
  const { data } = props;
  const { t } = useTranslation();
  const content = data.content;
  const loading = data.status === "in_progress";

  const [uiState, setUiState] = useState<"pending" | "skipped" | "done">(
    "pending",
  );
  const [commitModalOpen, setCommitModalOpen] = useState(false);
  const [commitMessage, setCommitMessage] = useState("");
  const [doPush, setDoPush] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [commitHash, setCommitHash] = useState("");
  const [expandedFile, setExpandedFile] = useState<string | null>(null);

  const first = content?.[0]?.data;
  const output = content?.[1]?.data?.output;
  const parsed = useMemo(() => parseGitProposeOutput(output), [output]);

  if (!content?.length) return null;

  const serverLabel = first?.server_label ? `${first.server_label} / ` : "";
  const toolName = first?.name ?? "propose_git_commit";
  const title = `${serverLabel}${toolName}`;
  const input = first?.arguments;

  if (loading || !parsed) {
    return (
      <div style={{ width: "100%" }}>
        {loading ? (
          <Spin style={{ display: "block", margin: "12px 0" }} />
        ) : null}
        <ToolCall
          loading={loading}
          defaultOpen={false}
          title={title === "undefined" ? "" : title}
          input={input as string | Record<string, unknown>}
          output={output as string | Record<string, unknown>}
        />
      </div>
    );
  }

  const err = parsed.error?.trim();
  const files = parsed.files ?? [];
  const repoPath = parsed.repo_path ?? "";
  const summary = parsed.summary ?? "";
  const totalAdd = parsed.total_additions ?? 0;
  const totalDel = parsed.total_deletions ?? 0;

  if (err) {
    return (
      <Card size="small" className={styles.card}>
        <Typography.Text type="danger">{err}</Typography.Text>
      </Card>
    );
  }

  if (files.length === 0) {
    return (
      <Card size="small" className={styles.card}>
        <Typography.Text type="secondary">
          {t("gitCommitCard.empty")}
        </Typography.Text>
      </Card>
    );
  }

  const openCommitModal = () => {
    setCommitMessage(summary.trim() || t("gitCommitCard.defaultMessage"));
    setCommitModalOpen(true);
  };

  const handleConfirmCommit = async () => {
    const msg = commitMessage.trim();
    if (!msg) {
      antdMessage.warning(t("gitCommitCard.messageRequired"));
      return;
    }
    setSubmitting(true);
    try {
      const res = await gitApi.commit({
        files: files.map((f) => f.path),
        message: msg,
        cwd: repoPath,
        push: doPush,
      });
      if (res.commit_hash) {
        setCommitHash(res.commit_hash);
      }
      setUiState("done");
      setCommitModalOpen(false);
      antdMessage.success(t("gitCommitCard.success"));
    } catch (e) {
      const detail =
        e instanceof Error ? e.message : t("gitCommitCard.commitFailed");
      antdMessage.error(detail);
    } finally {
      setSubmitting(false);
    }
  };

  const pendingActions = uiState === "pending";

  return (
    <div style={{ width: "100%" }}>
      <Card size="small" className={styles.card} title={t("gitCommitCard.title")}>
        <div className={styles.header}>
          {repoPath ? (
            <Typography.Text type="secondary" ellipsis>
              {repoPath}
            </Typography.Text>
          ) : null}
          <div className={styles.stats}>
            {t("gitCommitCard.stats", {
              count: files.length,
              add: totalAdd,
              del: totalDel,
            })}
          </div>
        </div>

        <div className={styles.actions}>
          <Button
            disabled={!pendingActions}
            onClick={() => {
              setUiState("skipped");
              antdMessage.info(t("gitCommitCard.skippedToast"));
            }}
          >
            {t("gitCommitCard.discard")}
          </Button>
          <Button type="primary" disabled={!pendingActions} onClick={openCommitModal}>
            {t("gitCommitCard.submit")}
          </Button>
        </div>

        {uiState === "skipped" ? (
          <Typography.Text type="secondary" style={{ display: "block", marginTop: 12 }}>
            {t("gitCommitCard.skipped")}
          </Typography.Text>
        ) : null}
        {uiState === "done" ? (
          <Typography.Text type="success" style={{ display: "block", marginTop: 12 }}>
            {t("gitCommitCard.committed")}
            {commitHash ? ` · ${commitHash.slice(0, 7)}` : ""}
          </Typography.Text>
        ) : null}

        <Collapse
          ghost
          className={styles.collapse}
          items={[
            {
              key: "files",
              label: t("gitCommitCard.expandFiles"),
              children: (
                <div>
                  {files.map((f) => {
                    const open = expandedFile === f.path;
                    return (
                      <div key={f.path}>
                        <div
                          role="button"
                          tabIndex={0}
                          className={styles.fileRow}
                          onClick={() =>
                            setExpandedFile(open ? null : f.path)
                          }
                          onKeyDown={(ev) => {
                            if (ev.key === "Enter" || ev.key === " ") {
                              ev.preventDefault();
                              setExpandedFile(open ? null : f.path);
                            }
                          }}
                        >
                          <Tag className={styles.statusTag}>{f.status}</Tag>
                          <span className={styles.filePath} title={f.path}>
                            {f.path}
                          </span>
                          <span className={styles.nums}>
                            +{f.additions} / -{f.deletions}
                          </span>
                        </div>
                        {open ? (
                          <div className={styles.diffWrap}>
                            <DiffViewer diff={f.diff || ""} />
                          </div>
                        ) : null}
                      </div>
                    );
                  })}
                </div>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        title={t("gitCommitCard.commitModalTitle")}
        open={commitModalOpen}
        onCancel={() => setCommitModalOpen(false)}
        footer={
          <Space>
            <Button onClick={() => setCommitModalOpen(false)}>
              {t("common.cancel")}
            </Button>
            <Button
              type="primary"
              loading={submitting}
              onClick={() => void handleConfirmCommit()}
            >
              {t("gitCommitCard.confirmCommit")}
            </Button>
          </Space>
        }
        destroyOnClose
      >
        <Input.TextArea
          rows={4}
          value={commitMessage}
          onChange={(e) => setCommitMessage(e.target.value)}
          placeholder={t("gitCommitCard.messagePlaceholder")}
        />
        <div style={{ marginTop: 12 }}>
          <Checkbox checked={doPush} onChange={(e) => setDoPush(e.target.checked)}>
            {t("gitCommitCard.pushAfterCommit")}
          </Checkbox>
        </div>
      </Modal>
    </div>
  );
}
