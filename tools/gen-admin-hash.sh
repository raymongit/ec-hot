#!/usr/bin/env bash
set -e
echo "== 拉取 caddy =="
docker pull caddy:2-alpine 2>&1 | tail -2

PASS=$(head -c 32 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 16)
HASH=$(docker run --rm caddy:2-alpine caddy hash-password --plaintext "$PASS")

echo "PASSWORD=$PASS"
echo "HASH=$HASH"
