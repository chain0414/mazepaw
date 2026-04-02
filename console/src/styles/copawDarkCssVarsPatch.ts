/**
 * 与 layout.css 中深色 copaw 变量块一致，但通过 JS 插入到 document.head **最后**，
 * 以压过 @agentscope-ai/design / antd 运行时注入的 `.css-var-rN` 样式（否则白底白字）。
 */
const COPAW_DARK_TOKEN_BLOCK = `
  --copaw-color-bg-base: #141414 !important;
  --copaw-color-bg-container: #1f1f1f !important;
  --copaw-color-bg-elevated: #1f1f1f !important;
  --copaw-color-bg-layout: #141414 !important;
  --copaw-color-text: rgba(255, 255, 255, 0.85) !important;
  --copaw-color-text-base: rgba(255, 255, 255, 0.88) !important;
  --copaw-color-text-secondary: rgba(255, 255, 255, 0.65) !important;
  --copaw-color-text-tertiary: rgba(255, 255, 255, 0.45) !important;
  --copaw-color-border: rgba(255, 255, 255, 0.12) !important;
  --copaw-color-border-secondary: rgba(255, 255, 255, 0.16) !important;
  --copaw-button-default-bg: #1f1f1f !important;
  --copaw-button-default-color: rgba(255, 255, 255, 0.88) !important;
  --copaw-button-default-border-color: rgba(255, 255, 255, 0.22) !important;
  --copaw-button-default-hover-bg: rgba(255, 255, 255, 0.08) !important;
  --copaw-button-default-hover-color: rgba(255, 255, 255, 0.95) !important;
  --copaw-button-default-hover-border-color: rgba(255, 255, 255, 0.3) !important;
  --copaw-button-default-active-bg: rgba(255, 255, 255, 0.12) !important;
  --copaw-button-default-active-color: rgba(255, 255, 255, 0.95) !important;
  --copaw-button-default-active-border-color: rgba(255, 255, 255, 0.35) !important;
  --copaw-button-text-text-color: rgba(255, 255, 255, 0.85) !important;
  --copaw-button-text-text-hover-color: rgba(255, 255, 255, 0.95) !important;
  --copaw-button-text-text-active-color: rgba(255, 255, 255, 0.95) !important;
  --copaw-button-default-ghost-color: rgba(255, 255, 255, 0.85) !important;
`;

export const COPAW_DARK_CSS_VARS_PATCH = `
/*
 * design 包 Switch 全局样式（styled-components）使用 var(--copaw-color-primary) / primary-bg。
 * App 内 cssVar:false 时 antd 不会往文档树注入这些变量；checked 时 var(--copaw-color-primary) 无效
 * 则声明被丢弃，回退到同文件里 .copaw-switch 的 primary-bg（#202041），与卡片背景几乎同色；
 * hover 时 antd 注入的 colorPrimaryHover 覆盖，才出现紫色。
 * 在 html 上补齐 bailianDark 主色变量即可（与 bailianDarkTheme.json 一致）。
 */
html.dark-mode {
  --copaw-color-primary: #5551cc !important;
  --copaw-color-primary-hover: #857de3 !important;
  --copaw-color-primary-bg: #202041 !important;
  --copaw-color-primary-border-hover: #373476 !important;
  --copaw-color-fill-disable: #8d8c98 !important;
}

/* 通用：任意带 css-var 的节点 */
html.dark-mode [class*="css-var"] {
${COPAW_DARK_TOKEN_BLOCK}
}
/* 更高优先级：按钮本体同时带 .copaw-btn 与 .css-var-rN，压过后续同元素上的 token 注入 */
html.dark-mode button.copaw-btn[class*="css-var"],
html.dark-mode .copaw-btn[class*="css-var"] {
${COPAW_DARK_TOKEN_BLOCK}
}
/* 直接写死背景/字色，避免仅改变量仍被 component 层 background 覆盖 */
html.dark-mode button.copaw-btn.copaw-btn-variant-outlined.copaw-btn-color-default:not(:disabled):not(.copaw-btn-disabled),
html.dark-mode button.copaw-btn.copaw-btn-variant-dashed.copaw-btn-color-default:not(:disabled):not(.copaw-btn-disabled),
html.dark-mode .copaw-btn.copaw-btn-variant-outlined.copaw-btn-color-default:not(:disabled):not(.copaw-btn-disabled),
html.dark-mode .copaw-btn.copaw-btn-variant-dashed.copaw-btn-color-default:not(:disabled):not(.copaw-btn-disabled) {
  background: #1f1f1f !important;
  background-color: #1f1f1f !important;
  color: rgba(255, 255, 255, 0.88) !important;
  border-color: rgba(255, 255, 255, 0.22) !important;
}
html.dark-mode button.copaw-btn.copaw-btn-variant-outlined.copaw-btn-color-default:not(:disabled):not(.copaw-btn-disabled) span,
html.dark-mode .copaw-btn.copaw-btn-variant-outlined.copaw-btn-color-default:not(:disabled):not(.copaw-btn-disabled) span {
  color: inherit !important;
}
/* Modal / Drawer / Popconfirm 底部与弹层内默认按钮 */
html.dark-mode .copaw-modal-footer .copaw-btn.copaw-btn-color-default.copaw-btn-variant-outlined:not(:disabled):not(.copaw-btn-disabled),
html.dark-mode .copaw-modal-footer .copaw-btn.copaw-btn-color-default.copaw-btn-variant-dashed:not(:disabled):not(.copaw-btn-disabled),
html.dark-mode .copaw-drawer-footer .copaw-btn.copaw-btn-color-default.copaw-btn-variant-outlined:not(:disabled):not(.copaw-btn-disabled),
html.dark-mode .copaw-drawer-footer .copaw-btn.copaw-btn-color-default.copaw-btn-variant-dashed:not(:disabled):not(.copaw-btn-disabled),
html.dark-mode .copaw-popconfirm .copaw-btn.copaw-btn-color-default.copaw-btn-variant-outlined:not(:disabled):not(.copaw-btn-disabled) {
  background: #1f1f1f !important;
  background-color: #1f1f1f !important;
  color: rgba(255, 255, 255, 0.88) !important;
  border-color: rgba(255, 255, 255, 0.22) !important;
}

/* Dropdown + Menu（Header 账号菜单等）：Portal 到 body，且带 menu-light，会固定浅色 */
html.dark-mode .copaw-dropdown[class*="css-var"],
html.dark-mode .ant-dropdown[class*="css-var"] {
  --copaw-color-bg-elevated: #1f1f1f !important;
}
html.dark-mode .copaw-dropdown .copaw-dropdown-menu,
html.dark-mode .copaw-dropdown-menu.copaw-dropdown-menu-root,
html.dark-mode .copaw-dropdown-menu.copaw-dropdown-menu-light,
html.dark-mode .ant-dropdown .ant-dropdown-menu,
html.dark-mode .ant-dropdown-menu.ant-dropdown-menu-root,
html.dark-mode .ant-dropdown-menu.ant-dropdown-menu-light {
  background: #1f1f1f !important;
  background-color: #1f1f1f !important;
  box-shadow: 0 6px 16px 0 rgba(0, 0, 0, 0.45) !important;
}
html.dark-mode .copaw-dropdown-menu-item,
html.dark-mode .ant-dropdown-menu-item {
  color: rgba(255, 255, 255, 0.85) !important;
}
html.dark-mode .copaw-dropdown-menu-item:hover,
html.dark-mode .copaw-dropdown-menu-item-active,
html.dark-mode .copaw-dropdown-menu-submenu-title:hover,
html.dark-mode .ant-dropdown-menu-item:hover,
html.dark-mode .ant-dropdown-menu-item-active,
html.dark-mode .ant-dropdown-menu-submenu-title:hover {
  background: rgba(255, 255, 255, 0.08) !important;
  color: rgba(255, 255, 255, 0.95) !important;
}
html.dark-mode .copaw-dropdown-menu-title-content,
html.dark-mode .ant-dropdown-menu-title-content {
  color: inherit !important;
}
html.dark-mode .copaw-dropdown-menu-item-icon,
html.dark-mode .copaw-dropdown-menu-item .anticon,
html.dark-mode .ant-dropdown-menu-item-icon,
html.dark-mode .ant-dropdown-menu-item .anticon {
  color: rgba(255, 255, 255, 0.65) !important;
}
html.dark-mode .copaw-dropdown-menu-item-divider,
html.dark-mode .ant-dropdown-menu-item-divider {
  background: rgba(255, 255, 255, 0.08) !important;
}
`;

export const COPAW_DARK_PATCH_STYLE_ID = "mazepaw-copaw-dark-css-vars-last";
