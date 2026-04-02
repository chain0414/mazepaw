import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Alert,
  Button,
  Input,
  Modal,
  Radio,
  Space,
  Steps,
  Typography,
  message,
} from "antd";
import { CopyOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import { credentialsApi } from "../../../api/modules/credentials";
import type { SSHKeyInfo } from "../../../api/types/credentials";

const GITHUB_SSH_NEW = "https://github.com/settings/ssh/new";

/** Matches backend `ssh_key_ops._KEY_NAME_RE`: letters, digits, ._- only */
function sanitizeKeyBasename(raw: string): string {
  const s = raw
    .replace(/[^a-zA-Z0-9_.-]/g, "_")
    .replace(/_+/g, "_")
    .replace(/^\.+|\.+$/g, "")
    .replace(/^_|_$/g, "");
  return s.slice(0, 48) || "key";
}

function filenameFromEmail(email: string): string | null {
  const e = email.trim();
  const at = e.indexOf("@");
  if (at <= 0) return null;
  const local = e.slice(0, at).trim();
  if (!local) return null;
  const base = sanitizeKeyBasename(local);
  if (!base) return null;
  return `id_ed25519_${base}`;
}

function randomDefaultKeyName(): string {
  const r = Math.random().toString(36).slice(2, 8);
  return `id_ed25519_copaw_${r}`;
}

type Props = {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
};

export default function GitHubCredentialWizard({
  open,
  onClose,
  onCreated,
}: Props) {
  const { t } = useTranslation();
  const [step, setStep] = useState(0);
  const [keys, setKeys] = useState<SSHKeyInfo[]>([]);
  const [selected, setSelected] = useState<SSHKeyInfo | null>(null);
  const [genOpen, setGenOpen] = useState(false);
  const [genName, setGenName] = useState("");
  const [genComment, setGenComment] = useState("");
  const genNameManualRef = useRef(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{
    success: boolean;
    message: string;
    github_username: string | null;
  } | null>(null);
  const [gitUserName, setGitUserName] = useState("");
  const [gitUserEmail, setGitUserEmail] = useState("");
  const [hostAlias, setHostAlias] = useState("");
  const [sshPreview, setSshPreview] = useState<string | null>(null);
  const [sshAfterApply, setSshAfterApply] = useState<string | null>(null);
  const [credName, setCredName] = useState("");
  const [saving, setSaving] = useState(false);

  const loadKeys = useCallback(async () => {
    try {
      const list = await credentialsApi.listSSHKeys();
      setKeys(list);
    } catch {
      setKeys([]);
    }
  }, []);

  useEffect(() => {
    if (!open) return;
    void loadKeys();
    setStep(0);
    setSelected(null);
    setTestResult(null);
    setGitUserName("");
    setGitUserEmail("");
    setHostAlias("");
    setSshPreview(null);
    setSshAfterApply(null);
    setCredName("");
  }, [open, loadKeys]);

  useEffect(() => {
    if (!genOpen) return;
    genNameManualRef.current = false;
    setGenName(randomDefaultKeyName());
    setGenComment("");
  }, [genOpen]);

  const effectiveKey = selected;

  const suggestedAlias = useMemo(() => {
    if (testResult?.github_username) {
      return `github.com-${testResult.github_username}`;
    }
    if (effectiveKey?.name) {
      return `github.com-${effectiveKey.name.replace(/^id_/, "")}`;
    }
    return "github.com-copaw";
  }, [testResult, effectiveKey]);

  useEffect(() => {
    if (step !== 4) return;
    setHostAlias((h) => h.trim() || suggestedAlias);
  }, [step, suggestedAlias]);

  useEffect(() => {
    if (step !== 3 || !effectiveKey) return;
    const c = effectiveKey.comment?.trim();
    if (c && c.includes("@")) {
      setGitUserEmail((prev) => prev || c);
    }
    if (testResult?.github_username) {
      setGitUserName((prev) => prev || testResult.github_username!);
    }
  }, [step, effectiveKey, testResult]);

  const copyText = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      message.success(t("credentials.wizard.copied"));
    } catch {
      message.error(t("credentials.wizard.copyFailed"));
    }
  };

  const runTest = async () => {
    if (!effectiveKey) return;
    setTesting(true);
    setTestResult(null);
    try {
      const r = await credentialsApi.testSSH({
        key_path: effectiveKey.private_path,
        host: "github.com",
      });
      setTestResult(r);
      if (r.success && r.github_username) {
        setGitUserName(r.github_username);
      }
    } catch (e) {
      console.error(e);
      message.error(t("credentials.wizard.testFailed"));
    } finally {
      setTesting(false);
    }
  };

  const previewSshBlock = async () => {
    if (!effectiveKey) return;
    const alias = hostAlias.trim() || suggestedAlias;
    const block = [
      "",
      `Host ${alias}`,
      "  HostName github.com",
      "  User git",
      `  IdentityFile ${effectiveKey.private_path}`,
      "  IdentitiesOnly yes",
      "",
    ].join("\n");
    let before = "";
    try {
      const r = await credentialsApi.getSSHConfig();
      before = r.content || "";
    } catch {
      before = "";
    }
    setSshPreview(`${before.trimEnd()}\n${block}`.trim() + "\n");
  };

  const applySsh = async () => {
    if (!effectiveKey) return;
    const alias = hostAlias.trim() || suggestedAlias;
    try {
      const r = await credentialsApi.applySSHConfig({
        host_alias: alias,
        hostname: "github.com",
        identity_file: effectiveKey.private_path,
        user: "git",
      });
      setSshAfterApply(r.full_content);
      message.success(t("credentials.wizard.sshApplied"));
    } catch (e: unknown) {
      console.error(e);
      message.error(
        e && typeof e === "object" && "message" in e
          ? String((e as { message?: string }).message)
          : t("credentials.wizard.sshApplyFailed"),
      );
    }
  };

  const saveCredential = async () => {
    if (!effectiveKey) return;
    const name = credName.trim();
    if (!name) {
      message.error(t("credentials.wizard.credNameRequired"));
      return;
    }
    if (!gitUserName.trim() || !gitUserEmail.trim()) {
      message.error(t("credentials.wizard.identityRequired"));
      return;
    }
    setSaving(true);
    try {
      await credentialsApi.create({
        type: "git",
        provider: "github",
        name,
        auth_method: "ssh_key_path",
        secret_ref: effectiveKey.private_path,
        metadata: {},
        acquisition_notes: "",
        git_user_name: gitUserName.trim(),
        git_user_email: gitUserEmail.trim(),
      });
      message.success(t("credentials.createSuccess"));
      onCreated();
      onClose();
    } catch (e) {
      console.error(e);
      message.error(t("credentials.saveFailed"));
    } finally {
      setSaving(false);
    }
  };

  const genKey = async () => {
    const n = genName.trim();
    if (!n) {
      message.error(t("credentials.wizard.keyNameRequired"));
      return;
    }
    try {
      const k = await credentialsApi.generateSSHKey({
        name: n,
        comment: genComment.trim(),
        key_type: "ed25519",
      });
      await loadKeys();
      setSelected(k);
      setGenOpen(false);
      genNameManualRef.current = false;
      setGenName("");
      setGenComment("");
      message.success(t("credentials.wizard.keyGenerated"));
    } catch (e) {
      console.error(e);
      message.error(t("credentials.wizard.keyGenFailed"));
    }
  };

  const canNext0 = !!selected;
  const canNext2 = testResult?.success === true;
  const canNext3 = gitUserName.trim() && gitUserEmail.trim();

  const next = () => {
    if (step === 0 && !canNext0) {
      message.warning(t("credentials.wizard.pickKey"));
      return;
    }
    if (step === 2 && !canNext2) {
      message.warning(t("credentials.wizard.testFirst"));
      return;
    }
    if (step === 3 && !canNext3) {
      message.warning(t("credentials.wizard.identityRequired"));
      return;
    }
    setStep((s) => Math.min(s + 1, 5));
  };

  const back = () => setStep((s) => Math.max(s - 1, 0));

  const stepItems = [
    { title: t("credentials.wizard.stepKeys") },
    { title: t("credentials.wizard.stepGithub") },
    { title: t("credentials.wizard.stepTest") },
    { title: t("credentials.wizard.stepIdentity") },
    { title: t("credentials.wizard.stepSshConfig") },
    { title: t("credentials.wizard.stepSave") },
  ];

  return (
    <>
      <Modal
        title={t("credentials.wizard.title")}
        open={open}
        onCancel={onClose}
        width={720}
        footer={null}
        destroyOnClose
        zIndex={1000}
      >
        <Steps current={step} items={stepItems} size="small" style={{ marginBottom: 24 }} />

        {step === 0 && (
          <div>
            <Typography.Paragraph>
              {t("credentials.wizard.keysIntro")}
            </Typography.Paragraph>
            <Radio.Group
              style={{ width: "100%" }}
              value={selected?.private_path}
              onChange={(e) => {
                const k = keys.find((x) => x.private_path === e.target.value);
                setSelected(k ?? null);
              }}
            >
              <Space direction="vertical" style={{ width: "100%" }}>
                {keys.map((k) => (
                  <Radio key={k.private_path} value={k.private_path}>
                    <code>{k.name}</code>{" "}
                    <Typography.Text type="secondary">
                      {k.key_type} {k.comment ? `· ${k.comment}` : ""}
                    </Typography.Text>
                  </Radio>
                ))}
              </Space>
            </Radio.Group>
            {keys.length === 0 && (
              <Alert type="info" showIcon message={t("credentials.wizard.noKeys")} />
            )}
            <Button style={{ marginTop: 12 }} onClick={() => setGenOpen(true)}>
              {t("credentials.wizard.generateKey")}
            </Button>
          </div>
        )}

        {step === 1 && effectiveKey && (
          <div>
            <Typography.Paragraph>
              {t("credentials.wizard.githubAddIntro")}
            </Typography.Paragraph>
            <Button
              type="link"
              href={GITHUB_SSH_NEW}
              target="_blank"
              rel="noreferrer"
              style={{ paddingLeft: 0 }}
            >
              {t("credentials.wizard.openGithubSsh")}
            </Button>
            <Typography.Paragraph strong style={{ marginTop: 16 }}>
              {t("credentials.wizard.publicKey")}
            </Typography.Paragraph>
            <Input.TextArea
              readOnly
              rows={6}
              value={effectiveKey.pub_content}
              style={{ fontFamily: "monospace", fontSize: 12 }}
            />
            <Button
              icon={<CopyOutlined />}
              style={{ marginTop: 8 }}
              onClick={() => void copyText(effectiveKey.pub_content)}
            >
              {t("credentials.wizard.copyPubKey")}
            </Button>
          </div>
        )}

        {step === 2 && effectiveKey && (
          <div>
            <Typography.Paragraph>{t("credentials.wizard.testIntro")}</Typography.Paragraph>
            <Button type="primary" loading={testing} onClick={() => void runTest()}>
              {t("credentials.wizard.runTest")}
            </Button>
            {testResult && (
              <Alert
                style={{ marginTop: 16 }}
                type={testResult.success ? "success" : "error"}
                message={
                  testResult.success
                    ? t("credentials.wizard.testOk", {
                        user: testResult.github_username ?? "",
                      })
                    : testResult.message.slice(0, 500)
                }
              />
            )}
          </div>
        )}

        {step === 3 && (
          <Space direction="vertical" style={{ width: "100%" }} size="middle">
            <div>
              <Typography.Text>{t("credentials.fields.gitUserName")}</Typography.Text>
              <Input
                value={gitUserName}
                onChange={(e) => setGitUserName(e.target.value)}
                placeholder={t("credentials.placeholders.gitUserName")}
              />
            </div>
            <div>
              <Typography.Text>{t("credentials.fields.gitUserEmail")}</Typography.Text>
              <Input
                value={gitUserEmail}
                onChange={(e) => setGitUserEmail(e.target.value)}
                placeholder={t("credentials.placeholders.gitUserEmail")}
              />
            </div>
          </Space>
        )}

        {step === 4 && effectiveKey && (
          <div>
            <Typography.Paragraph>{t("credentials.wizard.sshConfigIntro")}</Typography.Paragraph>
            <Typography.Text>{t("credentials.wizard.hostAlias")}</Typography.Text>
            <Input
              value={hostAlias}
              onChange={(e) => setHostAlias(e.target.value)}
              placeholder={suggestedAlias}
              style={{ marginBottom: 12 }}
            />
            <Space wrap>
              <Button onClick={() => void previewSshBlock()}>
                {t("credentials.wizard.previewConfig")}
              </Button>
              <Button type="primary" onClick={() => void applySsh()}>
                {t("credentials.wizard.applyConfig")}
              </Button>
              <Button type="link" onClick={() => setStep(5)}>
                {t("credentials.wizard.skipSshConfig")}
              </Button>
            </Space>
            {sshPreview && (
              <>
                <Typography.Paragraph strong style={{ marginTop: 16 }}>
                  {t("credentials.wizard.previewLabel")}
                </Typography.Paragraph>
                <Input.TextArea
                  readOnly
                  rows={12}
                  value={sshPreview}
                  style={{ fontFamily: "monospace", fontSize: 11 }}
                />
              </>
            )}
            {sshAfterApply && (
              <>
                <Typography.Paragraph strong style={{ marginTop: 16 }}>
                  {t("credentials.wizard.fullConfigLabel")}
                </Typography.Paragraph>
                <Input.TextArea
                  readOnly
                  rows={14}
                  value={sshAfterApply}
                  style={{ fontFamily: "monospace", fontSize: 11 }}
                />
              </>
            )}
          </div>
        )}

        {step === 5 && effectiveKey && (
          <Space direction="vertical" style={{ width: "100%" }} size="middle">
            <div>
              <Typography.Text>{t("credentials.fields.name")}</Typography.Text>
              <Input
                value={credName}
                onChange={(e) => setCredName(e.target.value)}
                placeholder={t("credentials.placeholders.name")}
              />
            </div>
            <Typography.Text type="secondary">
              {t("credentials.wizard.saveSummary", {
                key: effectiveKey.private_path,
              })}
            </Typography.Text>
          </Space>
        )}

        <div style={{ marginTop: 24, display: "flex", justifyContent: "space-between" }}>
          <Button onClick={step === 0 ? onClose : back}>
            {step === 0 ? t("common.cancel") : t("credentials.wizard.back")}
          </Button>
          <Space>
            {step < 5 && (
              <Button type="primary" onClick={next}>
                {t("credentials.wizard.next")}
              </Button>
            )}
            {step === 5 && (
              <Button type="primary" loading={saving} onClick={() => void saveCredential()}>
                {t("common.save")}
              </Button>
            )}
          </Space>
        </div>
      </Modal>

      <Modal
        title={t("credentials.wizard.generateTitle")}
        open={genOpen}
        onOk={() => void genKey()}
        onCancel={() => setGenOpen(false)}
        okText={t("credentials.wizard.generateConfirm")}
        zIndex={2000}
        getContainer={() => document.body}
      >
        <Typography.Text>{t("credentials.wizard.keyComment")}</Typography.Text>
        <Input
          value={genComment}
          onChange={(e) => {
            const v = e.target.value;
            setGenComment(v);
            if (!genNameManualRef.current) {
              const derived = filenameFromEmail(v);
              if (derived) setGenName(derived);
              else if (!v.trim()) setGenName(randomDefaultKeyName());
            }
          }}
          placeholder="you@example.com"
        />
        <Typography.Text style={{ display: "block", marginTop: 12 }}>
          {t("credentials.wizard.keyName")}
        </Typography.Text>
        <Typography.Paragraph type="secondary" style={{ marginBottom: 8, fontSize: 12 }}>
          {t("credentials.wizard.keyNameAutoHint")}
        </Typography.Paragraph>
        <Input
          value={genName}
          onChange={(e) => {
            genNameManualRef.current = true;
            setGenName(e.target.value);
          }}
          placeholder="id_ed25519_copaw_xxxxxx"
        />
      </Modal>
    </>
  );
}
