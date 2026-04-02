import { useCallback, useEffect, useState } from "react";
import {
  Button,
  Card,
  Form,
  Input,
  Modal,
  Popconfirm,
  Select,
  Space,
  Table,
  Tag,
  message,
} from "antd";
import { PlusOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import { credentialsApi } from "../../../api/modules/credentials";
import type { CredentialProfile } from "../../../api/types/credentials";
import { PageHeader } from "../Agents/components";
import GitHubCredentialWizard from "./GitHubCredentialWizard";
import styles from "./index.module.less";

const GIT_AUTH_PRESETS = [
  "ssh_key_env",
  "token_env",
  "oauth",
  "secret_ref",
];

export default function CredentialsPage() {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [profiles, setProfiles] = useState<CredentialProfile[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [wizardOpen, setWizardOpen] = useState(false);
  const [editing, setEditing] = useState<CredentialProfile | null>(null);
  const [form] = Form.useForm();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await credentialsApi.list();
      setProfiles(res.profiles);
    } catch (e) {
      console.error(e);
      message.error(t("credentials.loadFailed"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    void load();
  }, [load]);

  const gitProfiles = profiles.filter((p) => p.type === "git");

  const openWizard = () => {
    setWizardOpen(true);
  };

  const openEdit = (row: CredentialProfile) => {
    setEditing(row);
    form.setFieldsValue({
      ...row,
      git_user_name: row.git_user_name ?? "",
      git_user_email: row.git_user_email ?? "",
    });
    setModalOpen(true);
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      if (!editing) return;
      const next: CredentialProfile = {
        ...editing,
        ...values,
        git_user_name: values.git_user_name ?? "",
        git_user_email: values.git_user_email ?? "",
      };
      await credentialsApi.update(editing.id, next);
      message.success(t("credentials.updateSuccess"));
      setModalOpen(false);
      await load();
    } catch (e: unknown) {
      console.error(e);
      message.error(t("credentials.saveFailed"));
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await credentialsApi.delete(id);
      message.success(t("credentials.deleteSuccess"));
      await load();
    } catch (e) {
      console.error(e);
      message.error(t("credentials.deleteFailed"));
    }
  };

  return (
    <div className={styles.credentialsPage}>
      <PageHeader
        title={t("credentials.title")}
        description={t("credentials.pageDescription")}
        action={
          <Button type="primary" icon={<PlusOutlined />} onClick={openWizard}>
            {t("credentials.addGit")}
          </Button>
        }
      />

      <Card className={styles.tableCard} title={t("credentials.groups.git")}>
        <p className={styles.sectionDesc}>{t("credentials.gitHelp")}</p>
        <Table<CredentialProfile>
          rowKey="id"
          loading={loading}
          dataSource={gitProfiles}
          pagination={false}
          columns={[
            {
              title: t("credentials.columns.name"),
              dataIndex: "name",
              key: "name",
              render: (v, row) => v || row.id,
            },
            {
              title: t("credentials.columns.gitIdentity"),
              key: "git_identity",
              ellipsis: true,
              render: (_, row) => {
                const n = (row.git_user_name ?? "").trim();
                const e = (row.git_user_email ?? "").trim();
                if (!n && !e) return "—";
                if (n && e) return `${n} <${e}>`;
                return n || e;
              },
            },
            {
              title: t("credentials.columns.provider"),
              dataIndex: "provider",
              key: "provider",
            },
            {
              title: t("credentials.columns.authMethod"),
              dataIndex: "auth_method",
              key: "auth_method",
            },
            {
              title: t("credentials.columns.secretRef"),
              dataIndex: "secret_ref",
              key: "secret_ref",
              ellipsis: true,
            },
            {
              title: t("common.actions"),
              key: "actions",
              width: 160,
              render: (_, row) => (
                <Space>
                  <Button type="link" size="small" onClick={() => openEdit(row)}>
                    {t("common.edit")}
                  </Button>
                  <Popconfirm
                    title={t("credentials.deleteConfirm")}
                    onConfirm={() => handleDelete(row.id)}
                  >
                    <Button type="link" size="small" danger>
                      {t("common.delete")}
                    </Button>
                  </Popconfirm>
                </Space>
              ),
            },
          ]}
        />
      </Card>

      <Card
        className={`${styles.tableCard} ${styles.placeholderCard}`}
        title={t("credentials.groups.social")}
      >
        <Tag color="default">{t("credentials.comingSoon")}</Tag>
        <p className={styles.sectionDesc}>{t("credentials.socialHelp")}</p>
      </Card>

      <Card
        className={`${styles.tableCard} ${styles.placeholderCard}`}
        title={t("credentials.groups.deploy")}
      >
        <Tag color="default">{t("credentials.comingSoon")}</Tag>
        <p className={styles.sectionDesc}>{t("credentials.deployHelp")}</p>
      </Card>

      <GitHubCredentialWizard
        open={wizardOpen}
        onClose={() => setWizardOpen(false)}
        onCreated={() => void load()}
      />

      <Modal
        title={t("credentials.editTitle")}
        open={modalOpen}
        onOk={handleSave}
        onCancel={() => setModalOpen(false)}
        width={560}
        okText={t("common.save")}
        cancelText={t("common.cancel")}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label={t("credentials.fields.name")}
            rules={[{ required: true }]}
          >
            <Input placeholder={t("credentials.placeholders.name")} />
          </Form.Item>
          <Form.Item name="provider" label={t("credentials.fields.provider")}>
            <Input placeholder="github" />
          </Form.Item>
          <Form.Item
            name="auth_method"
            label={t("credentials.fields.authMethod")}
          >
            <Select options={GIT_AUTH_PRESETS.map((v) => ({ value: v, label: v }))} />
          </Form.Item>
          <Form.Item
            name="secret_ref"
            label={t("credentials.fields.secretRef")}
            extra={t("credentials.secretRefHelp")}
          >
            <Input placeholder="GITHUB_TOKEN / SSH_KEY_PATH …" />
          </Form.Item>
          <Form.Item
            name="git_user_name"
            label={t("credentials.fields.gitUserName")}
          >
            <Input placeholder={t("credentials.placeholders.gitUserName")} />
          </Form.Item>
          <Form.Item
            name="git_user_email"
            label={t("credentials.fields.gitUserEmail")}
          >
            <Input placeholder={t("credentials.placeholders.gitUserEmail")} />
          </Form.Item>
          <Form.Item
            name="acquisition_notes"
            label={t("credentials.fields.acquisitionNotes")}
          >
            <Input.TextArea rows={3} placeholder={t("credentials.placeholders.notes")} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
