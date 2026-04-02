import {
  cloneElement,
  isValidElement,
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactElement,
  type ReactNode,
} from "react";
import { useTranslation } from "react-i18next";
import { Avatar, Dropdown, Space, theme } from "antd";
import type { MenuProps } from "antd";
import {
  BookOutlined,
  DownOutlined,
  FileTextOutlined,
  LogoutOutlined,
  QuestionCircleOutlined,
  SunOutlined,
  MoonOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { authApi } from "../../api/modules/auth";
import { clearAuthToken, getApiToken } from "../../api/config";
import { useTheme } from "../../contexts/ThemeContext";
import styles from "./index.module.less";

const getWebsiteLang = (lang: string): string =>
  lang.startsWith("zh") ? "zh" : "en";

const getDocsUrl = (lang: string): string =>
  `https://copaw.agentscope.io/docs/intro?lang=${getWebsiteLang(lang)}`;

const getFaqUrl = (lang: string): string =>
  `https://copaw.agentscope.io/docs/faq?lang=${getWebsiteLang(lang)}`;

const getReleaseNotesUrl = (lang: string): string =>
  `https://copaw.agentscope.io/release-notes?lang=${getWebsiteLang(lang)}`;

function formatFallbackLabel(raw: string): string {
  if (!raw) return "";
  if (raw.startsWith("feishu:")) return raw.slice("feishu:".length);
  return raw;
}

export default function HeaderAccountMenu() {
  const { t, i18n } = useTranslation();
  const { token } = theme.useToken();
  const { isDark, toggleTheme } = useTheme();
  const [authEnabled, setAuthEnabled] = useState(false);
  const [displayLabel, setDisplayLabel] = useState("");
  const [avatarUrl, setAvatarUrl] = useState("");
  const [avatarImgOk, setAvatarImgOk] = useState(true);

  useEffect(() => {
    authApi
      .getStatus()
      .then((res) => setAuthEnabled(res.enabled))
      .catch(() => {});
  }, []);

  const refreshSession = useCallback(() => {
    authApi
      .verifySession()
      .then((r) => {
        if (r.valid && r.username) {
          const dn = (r.display_name ?? "").trim();
          const av = (r.avatar_url ?? "").trim();
          const fallback = formatFallbackLabel(r.username);
          setDisplayLabel(dn || fallback);
          setAvatarUrl(av);
          setAvatarImgOk(true);
        } else {
          setDisplayLabel("");
          setAvatarUrl("");
          setAvatarImgOk(true);
        }
      })
      .catch(() => {
        setDisplayLabel("");
        setAvatarUrl("");
      });
  }, []);

  useEffect(() => {
    refreshSession();
  }, [refreshSession]);

  useEffect(() => {
    const onStorage = (e: StorageEvent) => {
      if (e.key === "copaw_auth_token") refreshSession();
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, [refreshSession]);

  const openExternal = useCallback((url: string) => {
    if (!url) return;
    const pywebview = (window as unknown as { pywebview?: { api?: { open_external_link: (u: string) => void } } }).pywebview;
    if (pywebview?.api?.open_external_link) {
      pywebview.api.open_external_link(url);
    } else {
      window.open(url, "_blank");
    }
  }, []);

  const onMenuClick: MenuProps["onClick"] = ({ key }) => {
    switch (key) {
      case "theme":
        toggleTheme();
        break;
      case "changelog":
        openExternal(getReleaseNotesUrl(i18n.language));
        break;
      case "docs":
        openExternal(getDocsUrl(i18n.language));
        break;
      case "faq":
        openExternal(getFaqUrl(i18n.language));
        break;
      case "logout":
        clearAuthToken();
        window.location.href = "/login";
        break;
      default:
        break;
    }
  };

  const items: MenuProps["items"] = useMemo(() => {
    const base: MenuProps["items"] = [
      {
        key: "theme",
        icon: isDark ? <SunOutlined /> : <MoonOutlined />,
        label: t(isDark ? "theme.lightMode" : "theme.darkMode"),
      },
      {
        key: "changelog",
        icon: <FileTextOutlined />,
        label: t("header.changelog"),
      },
      {
        key: "docs",
        icon: <BookOutlined />,
        label: t("header.docs"),
      },
      {
        key: "faq",
        icon: <QuestionCircleOutlined />,
        label: t("header.faq"),
      },
    ];
    if (!authEnabled) return base;
    return [
      ...base,
      { type: "divider" },
      {
        key: "logout",
        icon: <LogoutOutlined />,
        label: t("login.logout"),
        className: styles.menuItemLogout,
      },
    ];
  }, [authEnabled, isDark, t]);

  const hasToken = Boolean(getApiToken());
  const showLabel = authEnabled && hasToken && displayLabel;
  const useRemoteAvatar = Boolean(avatarUrl && avatarImgOk);
  const avatarLetter = showLabel
    ? displayLabel.slice(0, 1).toUpperCase()
    : undefined;

  const menuProps: MenuProps = useMemo(
    () => ({
      items,
      onClick: onMenuClick,
      /** 否则 Dropdown 内 Menu 默认 theme=light，会得到 copaw-dropdown-menu-light */
      theme: isDark ? "dark" : "light",
    }),
    [items, onMenuClick, isDark],
  );

  /** Dropdown 先 createElement(Menu, menu) 再包 OverrideProvider；clone 一层确保 theme 命中内部 Menu */
  const accountMenuPopupRender = useCallback(
    (originNode: ReactNode) => {
      if (!isDark || !isValidElement(originNode)) {
        return originNode;
      }
      return cloneElement(originNode as ReactElement<MenuProps>, {
        theme: "dark",
      });
    },
    [isDark],
  );

  return (
    <Dropdown
      menu={menuProps}
      placement="bottomRight"
      trigger={["click"]}
      popupRender={accountMenuPopupRender}
    >
      <span
        className={styles.trigger}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            (e.currentTarget as HTMLElement).click();
          }
        }}
      >
        <Space size={8}>
          <Avatar
            size="small"
            src={useRemoteAvatar ? avatarUrl : undefined}
            icon={!avatarLetter && !useRemoteAvatar ? <UserOutlined /> : undefined}
            style={{
              flexShrink: 0,
              ...(useRemoteAvatar ? {} : { backgroundColor: token.colorPrimary }),
            }}
            onError={() => {
              setAvatarImgOk(false);
              return false;
            }}
          >
            {useRemoteAvatar ? undefined : avatarLetter}
          </Avatar>
          {showLabel ? (
            <span className={styles.userName} title={displayLabel}>
              {displayLabel}
            </span>
          ) : null}
          <DownOutlined className={styles.caret} />
        </Space>
      </span>
    </Dropdown>
  );
}
