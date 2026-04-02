import {
  createContext,
  useContext,
  useEffect,
  useLayoutEffect,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import {
  COPAW_DARK_CSS_VARS_PATCH,
  COPAW_DARK_PATCH_STYLE_ID,
} from "../styles/copawDarkCssVarsPatch";

function upsertCopawDarkPatchStyleAtEnd() {
  let el = document.getElementById(
    COPAW_DARK_PATCH_STYLE_ID,
  ) as HTMLStyleElement | null;
  if (!el) {
    el = document.createElement("style");
    el.id = COPAW_DARK_PATCH_STYLE_ID;
  }
  el.textContent = COPAW_DARK_CSS_VARS_PATCH;
  document.head.appendChild(el);
}

export type ThemeMode = "light" | "dark" | "system";
export type ResolvedTheme = "light" | "dark";

const STORAGE_KEY = "copaw-theme";

interface ThemeContextValue {
  /** User selected preference: light / dark / system */
  themeMode: ThemeMode;
  /** Resolved final theme after applying system preference */
  isDark: boolean;
  setThemeMode: (mode: ThemeMode) => void;
  /** Convenience toggle: light ↔ dark (skips system) */
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextValue>({
  themeMode: "light",
  isDark: false,
  setThemeMode: () => {},
  toggleTheme: () => {},
});

function getInitialMode(): ThemeMode {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "light" || stored === "dark" || stored === "system") {
      return stored;
    }
  } catch {
    // ignore storage errors
  }
  return "system";
}

function resolveIsDark(mode: ThemeMode): boolean {
  if (mode === "dark") return true;
  if (mode === "light") return false;
  // system
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ?? false;
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [themeMode, setThemeModeState] = useState<ThemeMode>(getInitialMode);
  const [isDark, setIsDark] = useState<boolean>(() =>
    resolveIsDark(getInitialMode()),
  );

  // Before paint: `html.dark-mode` must exist so layout.css + 下方补丁选择器生效
  useLayoutEffect(() => {
    const html = document.documentElement;
    if (isDark) {
      html.classList.add("dark-mode");
    } else {
      html.classList.remove("dark-mode");
    }
  }, [isDark]);

  /** 与首帧同步插入补丁，减少 Modal 打开时按钮仍显示浅色的闪动 */
  useLayoutEffect(() => {
    if (!isDark) {
      document.getElementById(COPAW_DARK_PATCH_STYLE_ID)?.remove();
      return;
    }
    upsertCopawDarkPatchStyleAtEnd();
  }, [isDark]);

  /**
   * Ant Design / design 会在运行时往 head 追加 `<style>`，顺序晚于 layout.css 与上一段 layoutEffect。
   * MutationObserver 把补丁 style 始终移到 head 末尾，压住 `.css-var-rN`。
   */
  useEffect(() => {
    if (!isDark) {
      return;
    }
    upsertCopawDarkPatchStyleAtEnd();
    const t = window.setTimeout(upsertCopawDarkPatchStyleAtEnd, 0);
    const observer = new MutationObserver(() => {
      requestAnimationFrame(upsertCopawDarkPatchStyleAtEnd);
    });
    observer.observe(document.head, { childList: true });
    return () => {
      window.clearTimeout(t);
      observer.disconnect();
      document.getElementById(COPAW_DARK_PATCH_STYLE_ID)?.remove();
    };
  }, [isDark]);

  // Listen to system theme changes when mode is "system"
  useEffect(() => {
    if (themeMode !== "system") return;

    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = (e: MediaQueryListEvent) => {
      setIsDark(e.matches);
    };
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, [themeMode]);

  const setThemeMode = useCallback((mode: ThemeMode) => {
    setThemeModeState(mode);
    setIsDark(resolveIsDark(mode));
    try {
      localStorage.setItem(STORAGE_KEY, mode);
    } catch {
      // ignore
    }
  }, []);

  const toggleTheme = useCallback(() => {
    setThemeMode(isDark ? "light" : "dark");
  }, [isDark, setThemeMode]);

  return (
    <ThemeContext.Provider
      value={{ themeMode, isDark, setThemeMode, toggleTheme }}
    >
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme(): ThemeContextValue {
  return useContext(ThemeContext);
}
