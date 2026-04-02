import { ToolCall } from "@agentscope-ai/chat";
import { Image, Typography } from "antd";
import { parseBrowserUseOutput } from "./browserUseToolRenderOutput";

/** Matches Tool.tsx runtime shape; package root does not export IAgentScopeRuntimeMessage. */
type ToolRenderData = {
  content?: Array<{
    data: {
      name?: string;
      server_label?: string;
      arguments?: unknown;
      output?: unknown;
    };
  }>;
  status?: string;
};

export default function BrowserUseToolRender(props: { data: ToolRenderData }) {
  const { data } = props;
  const content = data.content;

  if (!content?.length) return null;

  const loading = data.status === "in_progress";
  const first = content[0]?.data;
  const serverLabel = first?.server_label
    ? `${first.server_label} / `
    : "";
  const toolName = first?.name ?? "browser_use";
  const title = `${serverLabel}${toolName}`;

  const input = first?.arguments;
  const output = content[1]?.data?.output;
  const parsed = parseBrowserUseOutput(output);
  const imageUrl =
    parsed && typeof parsed.image_data_url === "string"
      ? parsed.image_data_url
      : undefined;

  if (!imageUrl) {
    return (
      <ToolCall
        loading={loading}
        defaultOpen={false}
        title={title === "undefined" ? "" : title}
        input={input as string | Record<string, unknown>}
        output={output as string | Record<string, unknown>}
      />
    );
  }

  const savedPath =
    parsed && typeof parsed.path === "string" && parsed.path ? parsed.path : "";

  return (
    <div style={{ width: "100%" }}>
      <div style={{ marginBottom: 12 }}>
        <Image
          src={imageUrl}
          alt="Screenshot"
          style={{ maxWidth: "100%", height: "auto" }}
          preview
        />
        {savedPath ? (
          <Typography.Text
            type="secondary"
            style={{ display: "block", marginTop: 8 }}
            copyable={{ text: savedPath }}
          >
            {savedPath}
          </Typography.Text>
        ) : null}
      </div>
      <ToolCall
        loading={loading}
        defaultOpen={false}
        title={title === "undefined" ? "" : title}
        input={input as string | Record<string, unknown>}
        output={output as string | Record<string, unknown>}
      />
    </div>
  );
}
