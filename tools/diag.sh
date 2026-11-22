#!/usr/bin/env bash
cd /mnt/c/Users/19024/Documents/ecommerce-hot/AIHOT

echo "== 表清单 =="
docker compose exec -T db psql -U aihot -d aihot -tAc "select table_name from information_schema.tables where table_schema='public' order by 1;" | tr '\n' ' '
echo
echo "== items 状态分布 =="
docker compose exec -T db psql -U aihot -d aihot -c "select status, count(*) from items group by 1 order by 2 desc;" 2>&1 | head -20
echo "== 最近 5 条 item =="
docker compose exec -T db psql -U aihot -d aihot -c "select id, status, left(title,40) as title, created_at from items order by created_at desc limit 5;" 2>&1 | head -15
echo "== worker 日志（最近 20 行，含错误）=="
docker compose logs --tail=20 worker 2>&1 | tail -20
