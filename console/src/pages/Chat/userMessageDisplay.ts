/**
 * Detect server-prepended bootstrap block (see copaw.agents.prompt.build_bootstrap_guidance).
 * Must avoid false positives: require BOOTSTRAP marker + a --- separator before user text.
 */
function stripBootstrapGuidancePrefix(text: string): string | null {
  const hasMarker =
    text.includes("# BOOTSTRAP MODE") ||
    text.includes("# 引导模式") ||
    /`BOOTSTRAP\.md`/.test(text);
  if (!hasMarker || !text.includes("---")) return null;

  const byNewline = text.split(/\n---\s*\n/);
  if (byNewline.length >= 2) {
    const tail = byNewline[byNewline.length - 1]?.trim();
    if (tail) return tail;
  }

  // Single-line or collapsed whitespace: "... instead. --- 让我们开启"
  const bySpaced = text.split(/\s+---\s+/);
  if (bySpaced.length >= 2) {
    const tail = bySpaced[bySpaced.length - 1]?.trim();
    if (tail) return tail;
  }

  return null;
}

/** Whether the stored user text is bootstrap guidance + user prompt (server-prefixed). */
export function isBootstrapPrefixedUserMessage(text: string): boolean {
  return stripBootstrapGuidancePrefix(text) !== null;
}

/**
 * For chat UI, show only the part after the bootstrap `---` separator so quick
 * prompts match what the user clicked.
 */
export function userMessageVisibleText(text: string): string {
  const tail = stripBootstrapGuidancePrefix(text);
  return tail ?? text;
}
