import { useMemo } from "react";
import { Bubble } from "@agentscope-ai/chat";
import {
  AgentScopeRuntimeContentType,
  type IAgentScopeRuntimeRequest,
} from "@agentscope-ai/chat/lib/AgentScopeRuntimeWebUI/core/AgentScopeRuntime/types";
import { userMessageVisibleText } from "../userMessageDisplay";

/**
 * Like AgentScopeRuntimeRequestCard, but user text is rendered as Markdown (raw: false)
 * and bootstrap-prefixed messages show only the user-facing tail after `---`.
 */
export default function CustomRequestCard(props: {
  data: IAgentScopeRuntimeRequest;
}) {
  const cards = useMemo(
    () =>
      props.data.input[0].content.reduce<{ code: string; data: unknown }[]>(
        (p, c) => {
          if (c.type === AgentScopeRuntimeContentType.TEXT) {
            p.push({
              code: "Text",
              data: {
                content: userMessageVisibleText(c.text ?? ""),
                raw: false,
              },
            });
          }

          if (c.type === AgentScopeRuntimeContentType.IMAGE) {
            const imageCard = p.find((item) => item.code === "Images");
            if (!imageCard) {
              p.push({
                code: "Images",
                data: [{ url: c.image_url }],
              });
            } else {
              (imageCard.data as { url: string }[]).push({ url: c.image_url! });
            }
          }

          if (c.type === AgentScopeRuntimeContentType.FILE) {
            const fileCard = p.find((item) => item.code === "Files");
            if (!fileCard) {
              p.push({
                code: "Files",
                data: [
                  {
                    url: c.file_url,
                    name: c.file_name,
                    size: c.file_size,
                  },
                ],
              });
            } else {
              (
                fileCard.data as { url?: string; name?: string; size?: number }[]
              ).push({
                url: c.file_url!,
                name: c.file_name,
                size: c.file_size,
              });
            }
          }
          return p;
        },
        [],
      ),
    [props.data.input],
  );

  if (!cards?.length) return null;

  return <Bubble role="user" cards={cards} />;
}
