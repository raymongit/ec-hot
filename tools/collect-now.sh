#!/usr/bin/env bash
set -e
cd /mnt/c/Users/19024/Documents/ecommerce-hot/AIHOT

IDS=$(node -e '
const fs=require("fs");
const d=JSON.parse(fs.readFileSync("industry/sources.json","utf8"));
console.log(d.sources.map(s=>s.id).join(" "));
' 2>/dev/null || true)

if [ -z "$IDS" ]; then
  IDS=$(python3 -c 'import json;print(" ".join(s["id"] for s in json.load(open("industry/sources.json"))["sources"]))')
fi

echo "== 信源数量: $(echo $IDS | wc -w) =="
echo "== 在 api 容器里手动触发一轮采集 =="
docker compose exec -T api node scripts/collect.ts $IDS 2>&1 | tail -30
