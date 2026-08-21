#!/bin/bash
# 建立 localhost.run 隧道并把输出写到文件（避免 QR 码刷屏）
# 用法: ./tunnel.sh  > tunnel.log 2>&1 &
ssh -o StrictHostKeyChecking=no \
    -o ServerAliveInterval=30 \
    -o ServerAliveCountMax=3 \
    -o ExitOnForwardFailure=yes \
    -R 80:localhost:4321 \
    nokey@localhost.run 2>&1 | grep -v "^\s*$" | head -60
