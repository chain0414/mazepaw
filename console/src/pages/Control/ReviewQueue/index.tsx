import { useEffect, useState } from "react";
import {
  Button,
  Card,
  Form,
  Input,
  Modal,
  Popconfirm,
  Space,
  Table,
  Tag,
  message,
} from "antd";
import { ReloadOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import api from "../../../api";
import type { ReviewQueueItem } from "../../../api/types/insights";
import styles from "./index.module.less";

function getSelectedAgentId(): string {
  try {
    const raw = localStorage.getItem("copaw-agent-storage");
    if (!raw) {
      return "console";
    }
    const parsed = JSON.parse(raw) as { state?: { selectedAgent?: string } };
    return parsed?.state?.selectedAgent || "console";
  } catch {
    return "console";
  }
}

export default function ReviewQueuePage() {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [resolvingId, setResolvingId] = useState<string>("");
  const [items, setItems] = useState<ReviewQueueItem[]>([]);
  const [mrModalOpen, setMrModalOpen] = useState(false);
  const [mrSubmitting, setMrSubmitting] = useState(false);
  const [form] = Form.useForm<{ title: string; summary: string; mrUrl?: string }>();

  const load = async () => {
    setLoading(true);
    try {
      setItems(await api.listReviewQueue());
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const submitMrReview = async () => {
    try {
      const values = await form.validateFields();
      setMrSubmitting(true);
      const now = new Date().toISOString();
      const payload: ReviewQueueItem = {
        id: crypto.randomUUID(),
        title: values.title.trim(),
        summary: values.summary.trim(),
        item_type: "merge_request",
        source_agent: getSelectedAgentId(),
        status: "pending",
        created_at: now,
        updated_at: now,
        repo_scope: [],
        action_payload: values.mrUrl?.trim()
          ? { mr_url: values.mrUrl.trim() }
          : {},
        resolution_note: "",
      };
      await api.createReviewQueueItem(payload);
      message.success(t("reviewQueue.submitMrSuccess"));
      form.resetFields();
      setMrModalOpen(false);
      await load();
    } catch (error) {
      if (error && typeof error === "object" && "errorFields" in error) {
        return;
      }
      console.error("Failed to create review item:", error);
      message.error(t("reviewQueue.submitMrFailed"));
    } finally {
      setMrSubmitting(false);
    }
  };

  const resolveItem = async (itemId: string, status: "approved" | "denied") => {
    setResolvingId(itemId);
    try {
      await api.resolveReviewQueueItem(itemId, status);
      message.success(t("reviewQueue.resolveSuccess"));
      await load();
    } catch (error) {
      console.error("Failed to resolve review item:", error);
      message.error(t("reviewQueue.resolveFailed"));
    } finally {
      setResolvingId("");
    }
  };

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <div className={styles.headerInfo}>
          <h1 className={styles.title}>{t("reviewQueue.title")}</h1>
          <p className={styles.description}>{t("reviewQueue.description")}</p>
        </div>
        <Space>
          <Button type="primary" onClick={() => setMrModalOpen(true)}>
            {t("reviewQueue.submitMrReview")}
          </Button>
          <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>
            {t("common.refresh")}
          </Button>
        </Space>
      </div>
      <Card>
        <Table
          rowKey="id"
          loading={loading}
          dataSource={items}
          pagination={{ pageSize: 10, showSizeChanger: false }}
          columns={[
            {
              title: t("reviewQueue.columns.title"),
              dataIndex: "title",
              key: "title",
            },
            {
              title: t("reviewQueue.columns.type"),
              dataIndex: "item_type",
              key: "item_type",
              render: (value: string) => <Tag>{value}</Tag>,
            },
            {
              title: t("reviewQueue.columns.status"),
              dataIndex: "status",
              key: "status",
              render: (value: string) => <Tag>{value}</Tag>,
            },
            {
              title: t("reviewQueue.columns.summary"),
              dataIndex: "summary",
              key: "summary",
              ellipsis: true,
            },
            {
              title: t("reviewQueue.columns.agent"),
              dataIndex: "source_agent",
              key: "source_agent",
            },
            {
              title: t("common.actions"),
              key: "actions",
              render: (_, record) => (
                <Space>
                  <Popconfirm
                    title={t("reviewQueue.approve")}
                    onConfirm={() => resolveItem(record.id, "approved")}
                    okText={t("common.confirm")}
                    cancelText={t("common.cancel")}
                  >
                    <Button
                      type="link"
                      disabled={record.status !== "pending"}
                      loading={resolvingId === record.id}
                    >
                      {t("reviewQueue.approve")}
                    </Button>
                  </Popconfirm>
                  <Popconfirm
                    title={t("reviewQueue.deny")}
                    onConfirm={() => resolveItem(record.id, "denied")}
                    okText={t("common.confirm")}
                    cancelText={t("common.cancel")}
                  >
                    <Button
                      type="link"
                      danger
                      disabled={record.status !== "pending"}
                      loading={resolvingId === record.id}
                    >
                      {t("reviewQueue.deny")}
                    </Button>
                  </Popconfirm>
                </Space>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        title={t("reviewQueue.submitMrReviewTitle")}
        open={mrModalOpen}
        onCancel={() => {
          setMrModalOpen(false);
          form.resetFields();
        }}
        onOk={submitMrReview}
        confirmLoading={mrSubmitting}
        destroyOnClose
        width={560}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="title"
            label={t("reviewQueue.mrTitle")}
            rules={[{ required: true, message: t("reviewQueue.mrTitleRequired") }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            name="summary"
            label={t("reviewQueue.mrSummary")}
            rules={[{ required: true, message: t("reviewQueue.mrSummaryRequired") }]}
          >
            <Input.TextArea rows={6} />
          </Form.Item>
          <Form.Item name="mrUrl" label={t("reviewQueue.mrUrl")}>
            <Input type="url" placeholder="https://" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
