#!/usr/bin/env bash
set -euo pipefail

# ===========================================
# MazePaw 源码部署脚本
# ===========================================
# 功能：从源码构建 Docker 镜像并启动服务
# 用法：在 mazepaw 仓库根目录执行，或通过 maze-deploy 调用
#
# 环境变量：
#   MAZE_DEPLOY_DIR  - maze-deploy 目录路径（若设置则使用其 docker-compose）
#   MAZEPAW_PORT     - 服务端口，默认 8088

MAZEPAW_PORT="${MAZEPAW_PORT:-8088}"

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

  # 1. 构建 Docker 镜像（从源码）
  log_info "构建 MazePaw Docker 镜像（含 console 前端）..."
  docker build -f deploy/Dockerfile -t maze/mazepaw:latest .

  # 2. 启动服务
  if [ -n "${MAZE_DEPLOY_DIR:-}" ] && [ -f "${MAZE_DEPLOY_DIR}/docker-compose.server.yml" ]; then
    log_info "使用 maze-deploy 编排启动: $MAZE_DEPLOY_DIR"
    docker compose -f "${MAZE_DEPLOY_DIR}/docker-compose.server.yml" up -d --no-deps mazepaw
  else
    log_info "独立模式启动容器..."
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
  if [ -n "${MAZE_DEPLOY_DIR:-}" ]; then
    log_info "  查看日志: docker compose -f ${MAZE_DEPLOY_DIR}/docker-compose.server.yml logs -f mazepaw"
    log_info "  重启服务: docker compose -f ${MAZE_DEPLOY_DIR}/docker-compose.server.yml restart mazepaw"
  else
    log_info "  查看日志: docker logs -f mazepaw"
    log_info "  重启服务: docker restart mazepaw"
  fi
}

main "$@"
