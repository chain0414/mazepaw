export function parseBrowserUseOutput(
  raw: unknown,
): Record<string, unknown> | null {
  if (raw == null) return null;

  let value: unknown = raw;

  if (typeof value === "string") {
    const text = value;
    try {
      value = JSON.parse(text);
    } catch {
      return null;
    }

    if (typeof value === "string") {
      try {
        value = JSON.parse(value);
      } catch {
        return null;
      }
    }
  }

  if (typeof value === "object" && value !== null && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }

  return null;
}
