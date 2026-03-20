#!/usr/bin/env bash
set -euo pipefail

# ===========================================
# MazePaw 源码部署脚本
# ===========================================
# 功能：从源码构建 Docker 镜像并启动服务
# 用法：在 mazepaw 仓库根目录执行，或通过 maze-deploy 调用
#
# 环境变量：
#   MAZE_DEPLOY_DIR   - 含 compose 文件的目录（maze-deploy 根或 instances/<name>/）
#   MAZE_COMPOSE_FILE - compose 文件名，默认 docker-compose.server.yml（主栈，已不再含 mazepaw）
#                       广州实例请设 MAZE_COMPOSE_FILE=docker-compose.yml 且
#                       MAZE_DEPLOY_DIR=.../maze-deploy/instances/guangzhou
#   MAZEPAW_PORT      - 独立 docker run 模式下的宿主机端口，默认 8088
#
#   Docker 构建加速（可选，需 Docker BuildKit，Docker 23+ 默认开启）：
#   MAZEPAW_APT_ALIYUN_MIRROR=1  - apt 使用 mirrors.aliyun.com（国内 ECS 强烈建议）
#   MAZEPAW_NPM_REGISTRY=https://... - 覆盖 npm registry（例: https://registry.npmmirror.com）

MAZEPAW_PORT="${MAZEPAW_PORT:-8088}"
MAZE_COMPOSE_FILE="${MAZE_COMPOSE_FILE:-docker-compose.server.yml}"

log_info() {
  echo -e "\033[32m[INFO]\033[0m $1"
}

log_warn() {
  echo -e "\033[33m[WARN]\033[0m $1"
}

log_error() {
  echo -e "\033[31m[ERROR]\033[0m $1"
}

main() {
  log_info "===== MazePaw 源码部署 ====="

  local repo_root
  repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
  cd "$repo_root"

  if ! command -v docker >/dev/null 2>&1; then
    log_error "未找到 docker。请先安装 Docker Engine: https://docs.docker.com/engine/install/"
    exit 127
  fi
  if ! docker compose version >/dev/null 2>&1 && ! command -v docker-compose >/dev/null 2>&1; then
    log_error "需要 Docker Compose（docker compose 或 docker-compose）"
    exit 127
  fi

  local compose_path=""
  if [ -n "${MAZE_DEPLOY_DIR:-}" ]; then
    compose_path="${MAZE_DEPLOY_DIR}/${MAZE_COMPOSE_FILE}"
  fi

  # 1. 构建 Docker 镜像（从源码）
  log_info "构建 MazePaw Docker 镜像（含 console 前端）..."
  local -a build_args=(-f deploy/Dockerfile -t maze/mazepaw:latest)
  if [[ "${MAZEPAW_APT_ALIYUN_MIRROR:-0}" == "1" ]]; then
    build_args+=(--build-arg APT_USE_ALIYUN_MIRROR=1)
  fi
  if [[ -n "${MAZEPAW_NPM_REGISTRY:-}" ]]; then
    build_args+=(--build-arg "NPM_CONFIG_REGISTRY=${MAZEPAW_NPM_REGISTRY}")
  fi
  docker build "${build_args[@]}" .

  # 2. 启动服务
  if [ -n "${MAZE_DEPLOY_DIR:-}" ] && [ -f "$compose_path" ]; then
    log_info "使用 compose 启动: $compose_path"
    docker compose -f "$compose_path" up -d --no-deps mazepaw
  else
    if [ -n "${MAZE_DEPLOY_DIR:-}" ]; then
      log_warn "未找到 $compose_path，改为独立 docker run"
    else
      log_info "未设置 MAZE_DEPLOY_DIR，独立模式启动容器..."
    fi
    if docker ps -aq --filter "name=^mazepaw$" | grep -q .; then
      docker rm -f mazepaw 2>/dev/null || true
    fi
    docker run -d \
      --name mazepaw \
      -p "127.0.0.1:${MAZEPAW_PORT}:8088" \
      -v mazepaw_data:/app/working \
      -v mazepaw_secrets:/app/working.secret \
      --restart unless-stopped \
      maze/mazepaw:latest
  fi

  log_info "===== MazePaw 部署完成 ====="
  log_info "本地端口: 127.0.0.1:$MAZEPAW_PORT"
  log_info ""
  log_info "常用命令:"
  if [ -n "${MAZE_DEPLOY_DIR:-}" ] && [ -f "$compose_path" ]; then
    log_info "  查看日志: docker compose -f $compose_path logs -f mazepaw"
    log_info "  重启服务: docker compose -f $compose_path restart mazepaw"
  else
    log_info "  查看日志: docker logs -f mazepaw"
    log_info "  重启服务: docker restart mazepaw"
  fi
}

main "$@"
