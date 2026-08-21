#!/bin/bash
# 自动重连隧道脚本：serveo 优先，localhost.run 备选
# 用法: bash tunnel_autoreconnect.sh <端口> <日志文件>
PORT="${1:-4321}"
LOG="${2:-/tmp/tunnel_autoreconnect.log}"
URL_FILE="/tmp/tunnel_url_${PORT}.txt"

log() { echo "[$(date '+%H:%M:%S')] $1" >> "$LOG"; }

try_serveo() {
    log "尝试 serveo.net ..."
    ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=30 \
        -o ServerAliveCountMax=3 -o ConnectTimeout=20 \
        -R 80:localhost:${PORT} serveo.net 2>&1 | while read -r line; do
        url=$(echo "$line" | grep -o 'https://[a-z0-9-]*\.serveousercontent\.com' | head -1)
        if [ -n "$url" ]; then
            echo "$url" > "$URL_FILE"
            log "✅ serveo URL: $url"
        fi
    done
}

try_localhostrun() {
    log "尝试 localhost.run ..."
    ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=30 \
        -o ServerAliveCountMax=3 -o ConnectTimeout=20 \
        -R 80:localhost:${PORT} nokey@localhost.run 2>&1 | while read -r line; do
        url=$(echo "$line" | grep -o 'https://[a-z0-9]*\.lhr\.life' | head -1)
        if [ -n "$url" ]; then
            echo "$url" > "$URL_FILE"
            log "✅ localhost.run URL: $url"
        fi
    done
}

log "🚀 隧道自动重连启动 (端口 $PORT)"
# 主循环：尝试连接，成功后等待（ssh 会持续运行直到断开）
while true; do
    try_serveo
    if [ -f "$URL_FILE" ]; then
        url=$(cat "$URL_FILE")
        log "隧道已建立: $url（等待断开后重连）"
        # ssh 断开后才会走到这里，等待 5 秒再重连
        sleep 5
        rm -f "$URL_FILE"
    fi
    try_localhostrun
    if [ -f "$URL_FILE" ]; then
        url=$(cat "$URL_FILE")
        log "隧道已建立: $url（等待断开后重连）"
        sleep 5
        rm -f "$URL_FILE"
    fi
    sleep 10
done
