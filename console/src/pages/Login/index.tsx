import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Button, Card, Form, Input, message } from "antd";
import { LockOutlined, UserOutlined } from "@ant-design/icons";
import { authApi } from "../../api/modules/auth";
import { setAuthToken, getApiUrl } from "../../api/config";
import { useTheme } from "../../contexts/ThemeContext";

function safeRedirectPath(raw: string | null): string {
  if (
    raw &&
    raw.startsWith("/") &&
    !raw.startsWith("//") &&
    !raw.includes("..")
  ) {
    return raw;
  }
  return "/chat";
}

export default function LoginPage() {
  const { isDark } = useTheme();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [loading, setLoading] = useState(false);
  const [isRegister, setIsRegister] = useState(false);
  const [hasUsers, setHasUsers] = useState(true);
  const [feishuAvailable, setFeishuAvailable] = useState(false);
  const [passwordAllowed, setPasswordAllowed] = useState(true);

  const mapDetailToMessage = useCallback(
    (detail: string): string => {
      const feishuPrefix = "login.feishuErrors.";
      const known = [
        "password_login_local_only",
        "registration_disabled_use_feishu",
        "access_denied",
        "no_code",
        "auth_failed",
        "forbidden_tenant",
        "feishu_not_configured",
      ];
      if (known.includes(detail)) {
        const key = `${feishuPrefix}${detail}`;
        return t(key);
      }
      return detail;
    },
    [t],
  );

  useEffect(() => {
    const token = searchParams.get("token");
    const oauthError = searchParams.get("error");
    const redirect = safeRedirectPath(searchParams.get("redirect"));

    if (token) {
      setAuthToken(token);
      navigate(redirect, { replace: true });
      window.history.replaceState({}, "", window.location.pathname);
      return;
    }

    if (oauthError) {
      message.error(mapDetailToMessage(oauthError));
      window.history.replaceState({}, "", window.location.pathname);
    }

    authApi
      .getStatus()
      .then((res) => {
        if (!res.enabled) {
          navigate("/chat", { replace: true });
          return;
        }
        setHasUsers(res.has_users);
        setFeishuAvailable(res.feishu_login_available);
        setPasswordAllowed(res.password_login_allowed);
        if (!res.has_users && !res.feishu_login_available) {
          setIsRegister(true);
        } else {
          setIsRegister(false);
        }
      })
      .catch(() => {});
  }, [navigate, searchParams, mapDetailToMessage]);

  const onFinish = async (values: { username: string; password: string }) => {
    setLoading(true);
    try {
      const redirect = safeRedirectPath(searchParams.get("redirect"));

      if (isRegister) {
        const res = await authApi.register(values.username, values.password);
        if (res.token) {
          setAuthToken(res.token);
          message.success(t("login.registerSuccess"));
          navigate(redirect, { replace: true });
        }
      } else {
        const res = await authApi.login(values.username, values.password);
        if (res.token) {
          setAuthToken(res.token);
          navigate(redirect, { replace: true });
        } else {
          message.info(t("login.authNotEnabled"));
          navigate(redirect, { replace: true });
        }
      }
    } catch (err) {
      const detail =
        err instanceof Error ? err.message : t("login.failed");
      message.error(mapDetailToMessage(detail));
    } finally {
      setLoading(false);
    }
  };

  const startFeishu = () => {
    const returnTo = safeRedirectPath(searchParams.get("redirect"));
    const url = `${getApiUrl("/auth/feishu")}?returnTo=${encodeURIComponent(returnTo)}`;
    window.location.href = url;
  };

  const showPasswordForm =
    passwordAllowed && (hasUsers || !feishuAvailable);
  const showFirstUserPasswordHint = !hasUsers && !feishuAvailable;

  return (
    <div
      style={{
        height: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: isDark
          ? "linear-gradient(135deg, #0f0f14 0%, #1a1a2e 100%)"
          : "linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)",
      }}
    >
      <Card
        style={{
          width: 400,
          boxShadow: "0 4px 24px rgba(0,0,0,0.1)",
          borderRadius: 12,
        }}
      >
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <img
            src={`${import.meta.env.BASE_URL}logo.png`}
            alt="CoPaw"
            style={{ height: 48, marginBottom: 12 }}
          />
          <h2 style={{ margin: 0, fontWeight: 600, fontSize: 20 }}>
            {isRegister ? t("login.registerTitle") : t("login.title")}
          </h2>
          {showFirstUserPasswordHint ? (
            <p
              style={{
                margin: "8px 0 0",
                color: "#666",
                fontSize: 13,
              }}
            >
              {t("login.firstUserHint")}
            </p>
          ) : null}
          {!hasUsers && feishuAvailable ? (
            <p
              style={{
                margin: "8px 0 0",
                color: "#666",
                fontSize: 13,
              }}
            >
              {t("login.feishuFirstUserHint")}
            </p>
          ) : null}
        </div>

        {feishuAvailable ? (
          <Button
            type="primary"
            block
            size="large"
            onClick={startFeishu}
            style={{
              height: 44,
              marginBottom: showPasswordForm ? 20 : 0,
              borderRadius: 8,
              fontWeight: 500,
            }}
          >
            {t("login.feishuLogin")}
          </Button>
        ) : null}

        {showPasswordForm ? (
          <Form
            layout="vertical"
            onFinish={onFinish}
            autoComplete="off"
            size="large"
          >
            <Form.Item
              name="username"
              rules={[
                { required: true, message: t("login.usernameRequired") },
              ]}
            >
              <Input
                prefix={<UserOutlined />}
                placeholder={t("login.usernamePlaceholder")}
                autoFocus={!feishuAvailable}
              />
            </Form.Item>

            <Form.Item
              name="password"
              rules={[
                { required: true, message: t("login.passwordRequired") },
              ]}
            >
              <Input.Password
                prefix={<LockOutlined />}
                placeholder={t("login.passwordPlaceholder")}
              />
            </Form.Item>

            <Form.Item style={{ marginBottom: 0, marginTop: 8 }}>
              <Button
                type={feishuAvailable ? "default" : "primary"}
                htmlType="submit"
                loading={loading}
                block
                style={{ height: 44, borderRadius: 8, fontWeight: 500 }}
              >
                {isRegister ? t("login.register") : t("login.submit")}
              </Button>
            </Form.Item>
          </Form>
        ) : null}
      </Card>
    </div>
  );
}
