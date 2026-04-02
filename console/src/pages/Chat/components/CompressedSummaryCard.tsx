import { Markdown } from "@agentscope-ai/chat";
import { DownOutlined, RightOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import { useMemo, useState } from "react";
import styles from "./CompressedSummaryCard.module.less";

export type CompressedSummaryCardData = {
  text: string;
};

/**
 * Renders like an inline assistant note: collapsible summary without nesting
 * Bubble+unknown card codes (the library only registers cards from options.cards).
 */
export default function CompressedSummaryCard(props: {
  data: CompressedSummaryCardData;
}) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const text = props.data?.text ?? "";
  const Icon = useMemo(() => (open ? DownOutlined : RightOutlined), [open]);

  return (
    <div className={styles.wrap}>
      <button
        type="button"
        className={styles.summaryButton}
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <Icon className={styles.summaryIcon} />
        {t("chat.compressedSummary.title")}
      </button>
      {open ? (
        <div className={styles.summaryBody}>
          <Markdown content={text} />
        </div>
      ) : null}
    </div>
  );
}
