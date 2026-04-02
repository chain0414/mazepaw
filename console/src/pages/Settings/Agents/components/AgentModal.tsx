import { type FocusEvent, useEffect, useState } from "react";
import { DeleteOutlined, PlusOutlined } from "@ant-design/icons";
import {
  Alert,
  Button,
  Col,
  Divider,
  Form,
  Input,
  Modal,
  Row,
  Select,
  Typography,
} from "antd";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import type { AgentSummary } from "@/api/types/agents";
import { credentialsApi } from "@/api/modules/credentials";
import type { CredentialProfile } from "@/api/types/credentials";
import styles from "./AgentModal.module.less";

function slugifyRepoId(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function parseGitRemote(raw: string): { id: string; name: string } | null {
  const value = raw.trim();
  if (!value) return null;

  const patterns = [
    /^(?:ssh:\/\/)?git@[^:/]+[:/]([^/]+)\/([^/]+?)(?:\.git)?\/?$/i,
    /^https?:\/\/[^/]+\/([^/]+)\/([^/]+?)(?:\.git)?\/?$/i,
  ];

  for (const pattern of patterns) {
    const match = value.match(pattern);
    if (!match) continue;
    const repoName = match[2];
    return {
      id: slugifyRepoId(repoName),
      name: repoName,
    };
  }

  return null;
}

interface AgentModalProps {
  open: boolean;
  editingAgent: AgentSummary | null;
  form: ReturnType<typeof Form.useForm>[0];
  onSave: () => Promise<void>;
  onCancel: () => void;
}

export function AgentModal({
  open,
  editingAgent,
  form,
  onSave,
  onCancel,
}: AgentModalProps) {
  const { t } = useTranslation();
  const templateId = Form.useWatch("template_id", form);
  const repoAssetsWatch = Form.useWatch("repo_assets", form);
  const gitCredentialIdWatch = Form.useWatch("git_credential_id", form);
  const [gitCredentials, setGitCredentials] = useState<CredentialProfile[]>([]);

  const repoCount = Array.isArray(repoAssetsWatch) ? repoAssetsWatch.length : 0;
  const showNoRepoAlert = templateId === "developer" && repoCount === 0;
  const showCredentialGuide =
    templateId === "developer" &&
    repoCount > 0 &&
    !(String(gitCredentialIdWatch ?? "").trim());

  useEffect(() => {
    if (!open) return;
    credentialsApi
      .list()
      .then((res) =>
        setGitCredentials(res.profiles.filter((p) => p.type === "git")),
      )
      .catch(() => setGitCredentials([]));
  }, [open]);

  const applyTemplateDefaults = (nextTemplateId: string) => {
    form.setFieldValue(
      "module_id",
      nextTemplateId === "developer" ? "codeops" : "general",
    );
    if (nextTemplateId === "general") {
      form.setFieldValue("repo_assets", []);
      form.setFieldValue("git_credential_id", undefined);
    }
    if (nextTemplateId === "oss_researcher") {
      form.setFieldValue("repo_assets", []);
      form.setFieldValue("git_credential_id", undefined);
    }
  };

  const handleRemoteBlur = (fieldIndex: number) => (
    event: FocusEvent<HTMLInputElement>,
  ) => {
    const parsed = parseGitRemote(event.target.value);
    if (!parsed) return;

    const repoAssets = [...(form.getFieldValue("repo_assets") ?? [])];
    const current = repoAssets[fieldIndex] ?? {};
    const next = { ...current };
    let changed = false;

    if (!String(current.id ?? "").trim() && parsed.id) {
      next.id = parsed.id;
      changed = true;
    }
    if (!String(current.name ?? "").trim() && parsed.name) {
      next.name = parsed.name;
      changed = true;
    }

    if (!changed) return;
    repoAssets[fieldIndex] = next;
    form.setFieldValue("repo_assets", repoAssets);
  };

  return (
    <Modal
      rootClassName={styles.agentModalRoot}
      title={
        editingAgent
          ? t("agent.editTitle", { name: editingAgent.name })
          : t("agent.createTitle")
      }
      open={open}
      onOk={onSave}
      onCancel={onCancel}
      width={800}
      okText={t("common.save")}
      cancelText={t("common.cancel")}
    >
      <Form
        form={form}
        layout="vertical"
        autoComplete="off"
        onValuesChange={(changed) => {
          if (changed.template_id) {
            applyTemplateDefaults(String(changed.template_id));
          }
        }}
      >
        {editingAgent && (
          <Form.Item name="id" label={t("agent.id")}>
            <Input disabled />
          </Form.Item>
        )}
        <Form.Item name="module_id" hidden>
          <Input />
        </Form.Item>
        <Form.Item
          name="template_id"
          label={t("agent.template")}
          initialValue="general"
        >
          <Select
            options={[
              { value: "general", label: t("agent.templates.general") },
              { value: "developer", label: t("agent.templates.developer") },
              {
                value: "oss_researcher",
                label: t("agent.templates.oss_researcher"),
              },
            ]}
          />
        </Form.Item>
        <Form.Item
          name="name"
          label={t("agent.name")}
          rules={[{ required: true, message: t("agent.nameRequired") }]}
        >
          <Input placeholder={t("agent.namePlaceholder")} />
        </Form.Item>
        <Form.Item name="description" label={t("agent.description")}>
          <Input.TextArea
            placeholder={t("agent.descriptionPlaceholder")}
            rows={3}
          />
        </Form.Item>
        <Form.Item
          name="workspace_dir"
          label={t("agent.workspace")}
          help={
            !editingAgent ? (
              <span className={styles.secondaryText}>
                {t("agent.workspaceHelp")}
              </span>
            ) : undefined
          }
        >
          <Input
            placeholder="~/.copaw/workspaces/my-agent"
            disabled={!!editingAgent}
          />
        </Form.Item>

        {templateId === "developer" && (
          <Form.Item
            name="git_credential_id"
            label={t("agent.gitCredential")}
            tooltip={t("agent.gitCredentialHint")}
          >
            <Select
              allowClear
              placeholder={t("agent.gitCredentialPlaceholder")}
              options={gitCredentials.map((c) => ({
                value: c.id,
                label: c.name?.trim() ? `${c.name} (${c.id})` : c.id,
              }))}
            />
          </Form.Item>
        )}

        {showNoRepoAlert && (
          <Alert
            type="warning"
            showIcon
            style={{ marginBottom: 16 }}
            message={t("agent.developerNoRepoAlert")}
          />
        )}

        {showCredentialGuide && (
          <Alert
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
            message={
              <span>
                {t("agent.gitCredentialPushHint")}{" "}
                <Link to="/credentials">{t("agent.goToCredentials")}</Link>
              </span>
            }
          />
        )}

        {templateId === "developer" && (
          <>
            <Divider orientation="left">{t("agent.boundRepos")}</Divider>
            <Typography.Paragraph className={styles.secondaryText}>
              {t("agent.developerRepoHint")}
            </Typography.Paragraph>
            <Form.List name="repo_assets">
              {(fields, { add, remove }) => (
                <>
                  {fields.map((field) => (
                    <div key={field.key} className={styles.repoCard}>
                      <Row gutter={16}>
                        <Col xs={24} md={12}>
                          <Form.Item
                            {...field}
                            name={[field.name, "id"]}
                            label={t("agent.repoId")}
                            rules={[{ required: true, message: t("agent.repoIdRequired") }]}
                          >
                            <Input placeholder={t("agent.repoIdPlaceholder")} />
                          </Form.Item>
                        </Col>
                        <Col xs={24} md={12}>
                          <Form.Item
                            {...field}
                            name={[field.name, "name"]}
                            label={t("agent.repoName")}
                            rules={[{ required: true, message: t("agent.repoNameRequired") }]}
                          >
                            <Input placeholder={t("agent.repoNamePlaceholder")} />
                          </Form.Item>
                        </Col>
                      </Row>

                      <Row gutter={16}>
                        <Col span={24}>
                          <Form.Item
                            {...field}
                            name={[field.name, "local_path"]}
                            label={t("agent.repoLocalPath")}
                            rules={[
                              {
                                required: true,
                                message: t("agent.repoLocalPathRequired"),
                              },
                            ]}
                          >
                            <Input placeholder={t("agent.repoLocalPathPlaceholder")} />
                          </Form.Item>
                        </Col>
                      </Row>

                      <Row gutter={16} align="bottom">
                        <Col xs={24} md={20}>
                          <Form.Item
                            {...field}
                            name={[field.name, "remote_url"]}
                            label={t("agent.repoRemoteUrl")}
                            extra={
                              <span className={styles.secondaryText}>
                                {t("agent.repoRemoteUrlHelp")}
                              </span>
                            }
                          >
                            <Input
                              placeholder="git@github.com:owner/repo.git"
                              onBlur={handleRemoteBlur(field.name)}
                            />
                          </Form.Item>
                        </Col>
                        <Col xs={24} md={4}>
                          <div className={styles.rowAction}>
                            <Button
                              type="link"
                              danger
                              icon={<DeleteOutlined />}
                              onClick={() => remove(field.name)}
                            >
                              {t("common.delete")}
                            </Button>
                          </div>
                        </Col>
                      </Row>
                    </div>
                  ))}
                  <Form.Item>
                    <Button
                      type="dashed"
                      className={styles.addRepoButton}
                      block
                      onClick={() =>
                        add({
                          id: "",
                          name: "",
                          local_path: "",
                          remote_url: "",
                        })
                      }
                      icon={<PlusOutlined />}
                    >
                      {t("agent.addRepo")}
                    </Button>
                  </Form.Item>
                </>
              )}
            </Form.List>
          </>
        )}

        {templateId === "oss_researcher" && (
          <Typography.Paragraph className={styles.secondaryText}>
            {t("agent.ossResearchDesc")}
          </Typography.Paragraph>
        )}
      </Form>
    </Modal>
  );
}
