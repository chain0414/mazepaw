# 不使用 # syntax=docker/dockerfile:1.x：该指令会从 Docker Hub 拉取 frontend 镜像，国内/受限网络易超时。
# BuildKit 内置解析器支持下方 RUN --mount=type=cache（Docker 20.10+，需 DOCKER_BUILDKIT=1）。
# -----------------------------------------------------------------------------
# Stage 1: build console frontend (dist not committed in repo).
# -----------------------------------------------------------------------------
# 优化：先复制 package.json/lock，利用 Docker 层缓存；仅改源码时跳过 npm ci
FROM agentscope-registry.ap-southeast-1.cr.aliyuncs.com/agentscope/node:slim AS console-builder
WORKDIR /app
ARG NPM_CONFIG_REGISTRY
ENV NPM_CONFIG_REGISTRY=${NPM_CONFIG_REGISTRY}
COPY console/package.json console/package-lock.json /app/console/
RUN --mount=type=cache,target=/root/.npm \
    cd /app/console && npm ci --include=dev
COPY console /app/console
RUN cd /app/console && npm run build

# -----------------------------------------------------------------------------
# Stage 2: runtime image with Python, Chromium, and app.
# -----------------------------------------------------------------------------
FROM agentscope-registry.ap-southeast-1.cr.aliyuncs.com/agentscope/node:slim

# 国内构建：docker build --build-arg APT_USE_ALIYUN_MIRROR=1（可选，见 deploy-from-source / 广州 README）
ARG APT_USE_ALIYUN_MIRROR=0

# ENV variables
ENV NODE_ENV=production
ENV WORKSPACE_DIR=/app
ENV COPAW_WORKING_DIR=/app/working
ENV COPAW_SECRET_DIR=/app/working.secret

# Feishu OAuth for Web Console (optional, with COPAW_AUTH_ENABLED=true at runtime):
# 1) In Feishu app → Security → add redirect URL: https://<host>/api/auth/callback/feishu
# 2) Runtime: FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_REDIRECT_URI (must match exactly),
#    FEISHU_ALLOWED_TENANT_KEYS (comma-separated; get tenant_key from token/user_info after one login)
# Optional: COPAW_PUBLIC_ORIGIN (if behind TLS proxy), COPAW_CONSOLE_BASE_PATH=/console

# Channel filtering: use COPAW_DISABLED_CHANNELS (exclusion, recommended)
# or COPAW_ENABLED_CHANNELS (whitelist). Override at runtime with -e.
ARG COPAW_DISABLED_CHANNELS="imessage"
ENV COPAW_DISABLED_CHANNELS=${COPAW_DISABLED_CHANNELS}
ARG COPAW_ENABLED_CHANNELS=""
ENV COPAW_ENABLED_CHANNELS=${COPAW_ENABLED_CHANNELS}

ARG DEBIAN_FRONTEND=noninteractive

# 单次 apt-get update，避免双层 RUN 清空 list 缓存导致重复拉索引；BuildKit 缓存加速重复构建
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    set -eux; \
    if [ "$APT_USE_ALIYUN_MIRROR" = "1" ]; then \
      for f in /etc/apt/sources.list /etc/apt/sources.list.d/*; do \
        [ -f "$f" ] || continue; \
        sed -i \
          -e 's|deb.debian.org|mirrors.aliyun.com|g' \
          -e 's|security.debian.org|mirrors.aliyun.com|g' \
          "$f"; \
      done; \
    fi; \
    apt-get update && apt-get install -y --fix-missing \
    curl  \
    python3  \
    python3-pip  \
    python3-venv \
    build-essential  \
    libssl-dev  \
    git  \
    supervisor  \
    vim  \
    gettext-base \
    xfce4 \
    xfce4-terminal \
    xvfb \
    dbus-x11 \
    fonts-wqy-zenhei \
    fonts-wqy-microhei \
    chromium \
    chromium-sandbox \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxtst6 \
    libnss3 \
    libglib2.0-0 \
    libdrm2 \
    libgbm1 \
    libasound2 \
    fonts-liberation \
    libu2f-udev \
  && rm -rf /var/lib/apt/lists/* \
  && apt-get clean


RUN sed -i 's/^CHROMIUM_FLAGS=""/CHROMIUM_FLAGS="--no-sandbox"/' /usr/bin/chromium

# Playwright: use system Chromium (already installed above).
ENV PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium
# Avoid Playwright downloading its own browser when executable_path is used.
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
# Indicate running in container (used e.g. for Chromium --no-sandbox).
ENV COPAW_RUNNING_IN_CONTAINER=1

WORKDIR ${WORKSPACE_DIR}

RUN python3 -m venv venv
ENV PATH="/app/venv/bin:$PATH"

COPY pyproject.toml setup.py README.md ./
COPY src ./src
# Inject console dist from build stage (repo does not commit dist).
COPY --from=console-builder /app/console/dist/ ./src/copaw/console/
RUN pip install --no-cache-dir .

# Init working dir with default config.json and HEARTBEAT.md (build time).
RUN copaw init --defaults --accept-security

# CoPaw app port (default 8088). Override at runtime with -e COPAW_PORT=3000.
ENV COPAW_PORT=8088

COPY deploy/config/supervisord.conf.template /etc/supervisor/conf.d/supervisord.conf.template
COPY --chmod=755 deploy/entrypoint.sh /entrypoint.sh

EXPOSE 8088

CMD ["/entrypoint.sh"]
