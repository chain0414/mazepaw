import { Layout, Space } from "antd";
import LanguageSwitcher from "../components/LanguageSwitcher";
import AgentSelector from "../components/AgentSelector";
import HeaderAccountMenu from "../components/HeaderAccountMenu";
import { useTranslation } from "react-i18next";
import { GithubOutlined } from "@ant-design/icons";
import { Button, Tooltip } from "@agentscope-ai/design";
import styles from "./index.module.less";

const { Header: AntHeader } = Layout;

// Constants
const GITHUB_URL = "https://github.com/agentscope-ai/CoPaw" as const;

const keyToLabel: Record<string, string> = {
  chat: "nav.chat",
  channels: "nav.channels",
  sessions: "nav.sessions",
  "cron-jobs": "nav.cronJobs",
  heartbeat: "nav.heartbeat",
  "daily-digest": "nav.dailyDigest",
  "review-queue": "nav.reviewQueue",
  skills: "nav.skills",
  tools: "nav.tools",
  mcp: "nav.mcp",
  "agent-config": "nav.agentConfig",
  workspace: "nav.workspace",
  models: "nav.models",
  environments: "nav.environments",
  security: "nav.security",
  "token-usage": "nav.tokenUsage",
  agents: "nav.agents",
  credentials: "nav.credentials",
  "voice-transcription": "nav.voiceTranscription",
};

interface HeaderProps {
  selectedKey: string;
}

export default function Header({ selectedKey }: HeaderProps) {
  const { t } = useTranslation();

  const handleNavClick = (url: string) => {
    if (url) {
      const pywebview = (window as any).pywebview;
      if (pywebview?.api) {
        pywebview.api.open_external_link(url);
      } else {
        window.open(url, "_blank");
      }
    }
  };

  return (
    <AntHeader className={styles.header}>
      <span className={styles.headerTitle}>
        {t(keyToLabel[selectedKey] || "nav.chat")}
      </span>
      <Space size="middle">
        <AgentSelector />
        <Tooltip title={t("header.github")}>
          <Button
            icon={<GithubOutlined />}
            type="text"
            onClick={() => handleNavClick(GITHUB_URL)}
          >
            {t("header.github")}
          </Button>
        </Tooltip>
        <LanguageSwitcher />
        <HeaderAccountMenu />
      </Space>
    </AntHeader>
  );
}
