import { useEffect, useState } from "react";
import { Button, Card, Space, Table, Tag, Typography } from "antd";
import { ReloadOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import api from "../../../api";
import type { DailyDigestItem } from "../../../api/types/insights";
import styles from "./index.module.less";

const { Text } = Typography;

export default function DailyDigestPage() {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [items, setItems] = useState<DailyDigestItem[]>([]);

  const load = async () => {
    setLoading(true);
    try {
      setItems(await api.listDailyDigests());
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <div className={styles.headerInfo}>
          <h1 className={styles.title}>{t("dailyDigest.title")}</h1>
          <p className={styles.description}>{t("dailyDigest.description")}</p>
        </div>
        <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>
          {t("common.refresh")}
        </Button>
      </div>
      <Card>
        <Table
          rowKey="id"
          loading={loading}
          dataSource={items}
          pagination={{ pageSize: 10, showSizeChanger: false }}
          columns={[
            {
              title: t("dailyDigest.columns.title"),
              dataIndex: "title",
              key: "title",
            },
            {
              title: t("dailyDigest.columns.summary"),
              dataIndex: "summary",
              key: "summary",
              ellipsis: true,
            },
            {
              title: t("dailyDigest.columns.sources"),
              key: "sources",
              render: (_, record) => (
                <Space wrap>
                  {record.sources.map((source) => (
                    <Tag key={source}>{source}</Tag>
                  ))}
                </Space>
              ),
            },
            {
              title: t("dailyDigest.columns.repoScope"),
              key: "repo_scope",
              render: (_, record) =>
                record.repo_scope.length === 0 ? (
                  <Text type="secondary">—</Text>
                ) : (
                  <Space wrap>
                    {record.repo_scope.map((repo) => (
                      <Tag key={repo}>{repo}</Tag>
                    ))}
                  </Space>
                ),
            },
            {
              title: t("dailyDigest.columns.agent"),
              dataIndex: "source_agent",
              key: "source_agent",
            },
            {
              title: t("dailyDigest.columns.createdAt"),
              dataIndex: "created_at",
              key: "created_at",
            },
          ]}
        />
      </Card>
    </div>
  );
}
