import styles from "./index.module.less";

function lineClass(line: string): string {
  if (line.startsWith("+++ ") || line.startsWith("--- ")) {
    return styles.diffMeta;
  }
  if (line.startsWith("+")) {
    return styles.diffAdd;
  }
  if (line.startsWith("-")) {
    return styles.diffDel;
  }
  if (line.startsWith("@@")) {
    return styles.diffHunk;
  }
  return styles.diffCtx;
}

export function DiffViewer({ diff }: { diff: string }) {
  const lines = diff.split("\n");
  return (
    <pre className={styles.diffPre}>
      {lines.map((line, i) => (
        <div key={i} className={lineClass(line)}>
          {line || " "}
        </div>
      ))}
    </pre>
  );
}
