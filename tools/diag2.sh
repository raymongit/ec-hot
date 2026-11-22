#!/usr/bin/env bash
cd /mnt/c/Users/19024/Documents/ecommerce-hot/AIHOT
echo "== 数据量 =="
docker compose exec -T db psql -U aihot -d aihot -tAc "select 'articles='||count(*) from articles; select 'facts='||count(*) from facts; select 'stories='||count(*) from stories; select 'publications='||count(*) from publications; select 'articles_without_fact='||count(*) from articles a where not exists (select 1 from facts f where f.article_id=a.id);" 2>&1 | head -10
echo "== 最近采集批次 =="
docker compose exec -T db psql -U aihot -d aihot -tAc "select source_id||' | '||status||' | '||created_at from fetch_runs order by created_at desc limit 5;" 2>&1 | head -8
echo "== worker 是否有报错（全部日志里的 error 数）=="
docker compose logs worker 2>&1 | grep -c '"level":"error"'
docker compose logs worker 2>&1 | grep '"level":"error"' | tail -2
