#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""电商 HOT · 每日电商热点早报 → 飞书

流程：抓取信源 RSS/Atom → 去重与时间窗筛选 → 大模型打分精选 + 写中文标题摘要
      → 生成飞书卡片 → 用企业自建应用机器人推送到群。

用法：
    python aihot.py                 # 正式跑一次并推送
    python aihot.py --dry-run       # 只抓取和精选，把卡片写到 state/card-preview.json
    python aihot.py --no-llm        # 不调大模型，用规则排序兜底
    python aihot.py --test          # 发一张示例卡片，验证飞书链路
    python aihot.py --list-chats    # 列出机器人所在群，拿 chat_id
"""

from __future__ import annotations

import argparse
import gzip
import html
import json
import os
import re
import ssl
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent
TZ = timezone(timedelta(hours=8))
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

if sys.stdout is not None:  # pythonw.exe 下 stdout 是 None
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# --------------------------------------------------------------------------- 基础工具

def load_env(path: Path) -> None:
    """极简 .env 解析，不覆盖已存在的环境变量。"""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip().lstrip("\ufeff")
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


def log(msg: str) -> None:
    stamp = datetime.now(TZ).strftime("%H:%M:%S")
    line = f"[{stamp}] {msg}"
    try:
        print(line, flush=True)
    except Exception:
        pass
    try:
        log_dir = ROOT / "logs"
        log_dir.mkdir(exist_ok=True)
        with open(log_dir / f"aihot-{datetime.now(TZ):%Y-%m-%d}.log", "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception:
        pass


def now() -> datetime:
    return datetime.now(TZ)


def rel_time(dt: datetime) -> str:
    delta = now() - dt
    minutes = delta.total_seconds() / 60
    if minutes < 60:
        return f"{max(1, int(minutes))} 分钟前"
    if minutes < 24 * 60:
        return f"{int(minutes // 60)} 小时前"
    if minutes < 48 * 60:
        return f"昨天 {dt:%H:%M}"
    return f"{dt:%m-%d %H:%M}"


def http_get(url: str, timeout: int = 25) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
            "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8",
        },
    )
    # 显式给 context：某些站点（如 mistral.ai）在默认上下文下 TLS 握手会 EOF
    opener, fallback = _openers()
    try:
        with opener.open(req, timeout=timeout) as resp:
            return _read(resp)
    except Exception as exc:  # noqa: BLE001
        # 代理中途挂掉/隧道失败时，立刻改直连再试一次
        if opener is not fallback and _looks_like_proxy_error(exc):
            log(f"代理不可用（{type(exc).__name__}），本次改用直连")
            with fallback.open(req, timeout=timeout) as resp:
                return _read(resp)
        raise


def _read(resp) -> bytes:
    raw = resp.read()
    if resp.headers.get("Content-Encoding", "").lower() == "gzip":
        raw = gzip.decompress(raw)
    return raw


def _looks_like_proxy_error(exc: Exception) -> bool:
    text = f"{exc} {getattr(exc, 'reason', '')}".lower()
    return any(k in text for k in ("refused", "tunnel connection failed", "proxy", "407", "10061"))


_OPENERS: tuple | None = None
_OPENERS_LOCK = threading.Lock()


def _openers() -> tuple:
    """返回 (默认 opener, 直连 opener)。

    系统的「系统代理」设置如果残留（加速器已退出、但注册表还指着 127.0.0.1:7897），
    urllib 会在 Windows 上自动读取它，结果所有请求都打到没人监听的端口。
    所以先探活：代理端口不通就直接走直连。
    """
    global _OPENERS
    if _OPENERS is not None:
        return _OPENERS

    with _OPENERS_LOCK:
        if _OPENERS is not None:
            return _OPENERS

        # 显式 HTTPSHandler(context=...)：mistral.ai 等在 urllib 的默认上下文下 TLS 握手会 EOF
        tls = urllib.request.HTTPSHandler(context=ssl.create_default_context())
        direct = urllib.request.build_opener(urllib.request.ProxyHandler({}), tls)
        try:
            proxies = urllib.request.getproxies()
        except Exception:
            proxies = {}

        endpoint = proxies.get("https") or proxies.get("http") or ""
        if endpoint and not _proxy_alive(endpoint):
            log(f"系统代理 {endpoint} 没有响应（加速器已关？），本次全部直连")
            _OPENERS = (direct, direct)
            return _OPENERS

        if endpoint:
            log(f"检测到可用代理 {endpoint}，海外信源走代理")
            _OPENERS = (urllib.request.build_opener(tls), direct)
        else:
            log("没有配置代理，全部直连")
            _OPENERS = (direct, direct)
        return _OPENERS


def _proxy_alive(endpoint: str, timeout: float = 1.5) -> bool:
    import socket

    target = endpoint.split("://", 1)[-1]
    host, _, port = target.rpartition(":")
    if not host or not port.isdigit():
        host, port = target, "80"
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except Exception:
        return False


def http_json(url: str, payload: dict | None = None, headers: dict | None = None,
              timeout: int = 60, method: str | None = None) -> dict:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method or ("POST" if data else "GET"))
    req.add_header("Content-Type", "application/json; charset=utf-8")
    for k, v in (headers or {}).items():
        req.add_header(k, v)

    opener, fallback = _openers()
    try:
        with opener.open(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        if opener is not fallback and _looks_like_proxy_error(exc):
            log(f"代理返回错误（{exc.code}），本次改用直连")
            with fallback.open(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        raise RuntimeError(f"HTTP {exc.code} {url}: {body[:600]}") from None
    except Exception as exc:  # noqa: BLE001
        if opener is not fallback and _looks_like_proxy_error(exc):
            log(f"代理不可用（{type(exc).__name__}），本次改用直连")
            with fallback.open(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        raise


# --------------------------------------------------------------------------- 抓取与解析

TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")


def clean_text(value: str | None, limit: int | None = None) -> str:
    if not value:
        return ""
    text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", value)
    text = TAG_RE.sub(" ", text)
    text = html.unescape(text)
    text = WS_RE.sub(" ", text).strip()
    if limit and len(text) > limit:
        text = text[:limit].rstrip() + "…"
    return text


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower() if isinstance(tag, str) else ""


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    for parser in (
        lambda v: parsedate_to_datetime(v),
        lambda v: datetime.fromisoformat(v.replace("Z", "+00:00")),
    ):
        try:
            dt = parser(value)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(TZ)
        except Exception:
            continue
    return None


def parse_feed(raw: bytes) -> tuple[list[dict], str]:
    """返回 (条目列表, 格式说明)。支持 RSS 2.0 / Atom。"""
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise ValueError(f"XML 解析失败：{exc}") from None

    kind = local(root.tag)
    if kind not in ("rss", "feed", "rdf"):
        raise ValueError(f"不是 RSS/Atom（根节点 {kind}）")

    nodes = []
    for elem in root.iter():
        if local(elem.tag) in ("item", "entry"):
            nodes.append(elem)
    items = []
    for node in nodes:
        fields: dict[str, str] = {}
        for child in node:
            key = local(child.tag)
            if key == "link":
                href = (child.get("href") or "").strip()
                rel = (child.get("rel") or "alternate").strip()
                text = clean_text(child.text)
                if href and rel in ("alternate", ""):
                    fields.setdefault("link", href)
                elif text and not href:
                    fields.setdefault("link", text)
                continue
            if key in ("title", "description", "summary", "content", "encoded", "published",
                       "updated", "pubdate", "date", "guid", "id", "category"):
                if not child.text and len(child):
                    continue
                fields.setdefault(key, child.text or "")
        title = clean_text(fields.get("title"), 300)
        link = (fields.get("link") or fields.get("guid") or fields.get("id") or "").strip()
        summary = clean_text(
            fields.get("description") or fields.get("summary") or fields.get("content")
            or fields.get("encoded"), 700)
        if not title or not link:
            continue
        published = None
        for key in ("published", "pubdate", "updated", "date"):
            published = parse_datetime(fields.get(key))
            if published:
                break
        items.append({"title": title, "url": link, "summary": summary, "published": published})
    return items, kind


def fetch_source(source: dict, timeout: int = 15) -> tuple[dict, list[dict], str | None]:
    last_error = None
    for attempt in range(2):
        try:
            raw = http_get(source["url"], timeout)
            items, kind = parse_feed(raw)
            for item in items:
                item["source"] = source["name"]
                item["source_id"] = source["id"]
                item["tier"] = source.get("tier", "T2")
            return source, items, None
        except Exception as exc:  # noqa: BLE001
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))
    return source, [], last_error[:220] if last_error else "unknown"


# --------------------------------------------------------------------------- 筛选

def title_key(title: str) -> str:
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", title.lower())


def normalize_url(url: str) -> str:
    try:
        parts = urllib.parse.urlsplit(url)
        query = urllib.parse.parse_qsl(parts.query)
        kept = [(k, v) for k, v in query if not k.lower().startswith(("utm_", "ref", "source", "spm"))]
        return urllib.parse.urlunsplit((parts.scheme, parts.netloc.lower(), parts.path.rstrip("/"),
                                        urllib.parse.urlencode(kept), ""))
    except Exception:
        return url


def collect(cfg: dict) -> tuple[list[dict], dict]:
    sources = cfg["sources"]
    stats = {"sources": len(sources), "ok": 0, "failed": [], "raw_items": 0}
    results: list[tuple[dict, list[dict], str | None]] = []
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = [pool.submit(fetch_source, s) for s in sources]
        for fut in as_completed(futures):
            results.append(fut.result())

    pool_items: list[dict] = []
    for source, items, err in results:
        if err:
            stats["failed"].append(f"{source['name']}: {err}")
            continue
        stats["ok"] += 1
        stats["raw_items"] += len(items)
        pool_items.extend(items)

    cutoff = now() - timedelta(hours=cfg["lookback_hours"])
    seen = load_state().get("urls", {})
    seen_keys = set(load_state().get("titles", {}).keys())

    fresh, urls, keys = [], set(), set()
    for item in pool_items:
        url_key = normalize_url(item["url"])
        if url_key in urls or url_key in seen:
            continue
        key = title_key(item["title"])
        if len(key) < 8 and not re.search(r"[\u4e00-\u9fff]", key):
            continue
        if key in keys or key in seen_keys:
            continue
        published = item.get("published")
        if published and published < cutoff:
            continue
        urls.add(url_key)
        keys.add(key)
        item["url_key"] = url_key
        item["title_key"] = key
        fresh.append(item)

    # 新到旧的顺序，无时间的排后面
    fresh.sort(key=lambda it: it.get("published") or datetime.min.replace(tzinfo=TZ), reverse=True)
    stats["candidates"] = len(fresh)
    return fresh[: cfg["max_candidates"]], stats


def load_state() -> dict:
    path = ROOT / "state" / "seen.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(fresh_items: list[dict]) -> None:
    state = load_state()
    urls = state.get("urls", {})
    titles = state.get("titles", {})
    stamp = now().isoformat(timespec="seconds")
    for item in fresh_items:
        urls[item.get("url_key") or normalize_url(item["url"])] = stamp
        titles[item.get("title_key") or title_key(item["title"])] = stamp
    limit = now() - timedelta(days=14)
    urls = {k: v for k, v in urls.items() if _parse_iso(v) and _parse_iso(v) > limit}
    titles = {k: v for k, v in titles.items() if _parse_iso(v) and _parse_iso(v) > limit}
    path = ROOT / "state" / "seen.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps({"urls": urls, "titles": titles}, ensure_ascii=False, indent=1),
                    encoding="utf-8")


def _parse_iso(value: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(value)
        return dt if dt.tzinfo else dt.replace(tzinfo=TZ)
    except Exception:
        return None


# --------------------------------------------------------------------------- 大模型精选

SYSTEM_PROMPT = """你是《电商 HOT》的中文主编，每天早上给一位电商从业者（内容与策略方向）挑电商行业要闻。

判断重要性的标准，从高到低：
1. 平台规则与政策的实质变化：规则、费率、入口、治理、结算与处罚口径变了；
2. 大促节奏与流量机制：平台补贴、活动玩法、流量分配与算法机制变化；
3. 监管与合规：处罚、新规、执法动作、直播带货合规；
4. 竞对与行业格局：财报、融资并购、组织调整、新业务、跨境平台动作；
5. 品类与供给趋势：新品类、爆品、白牌与品牌格局、零售业态变化；
6. 达人直播生态：头部主播、机构、内容电商玩法；
7. 物流支付与基础设施。

以下一律不选：纯商品软文、带货广告与种草、培训机构招生、招商加盟、无信息量通稿、旧闻重发、纯情绪输出、招聘、活动预告、标题党。
同一件事被多家报道时只保留信息最全的一条，其余丢掉。
严禁编造原文里没有的平台、数字和结论；不确定就写得保守。

输出必须是 JSON 对象，不要 markdown 代码块，不要解释。"""

USER_TEMPLATE = """今天是 {today}。下面是过去 {hours} 小时内抓到的 {count} 条候选。请为每条按「电商从业者今天是否该知道」打分，挑出所有 ≥6 分的条目（最多 {max_items} 条），按分数从高到低排列。目标 8-12 条：如果 ≥6 分的不足 8 条，就如实只输出够格的条目，不要凑数、不要混入与电商无关的科技新闻。

候选（idx / 来源 / 时间 / 标题 / 摘要）：
{candidates}

只输出这个 JSON 结构：
{{"digest": "一句话概括今天电商圈最值得注意的事，40 字以内",
  "items": [
    {{"idx": 0, "score": 9, "event": "淘宝仅退款新规", "title": "中文标题，30 字以内，说清主体和事件", "summary": "60-110 字，先给结论再给关键事实，不要复读标题", "tag": "平台规则"}}
  ]}}

score 为 1-10 的整数，8 分以上是「今天不看会影响经营判断」。tag 只能从：平台规则、大促玩法、品类趋势、跨境、直播达人、物流支付、监管、数据报告、观点 里选一个。
event 是这件事的归一化标签（3-8 个字符，主体+事件，例如「淘宝仅退款」「双11节奏」「Temu 半托管」）。
同一件事的多篇报道必须用完全相同的 event，并且只保留信息最全的一篇进 items，其余不要输出。
items 按 score 从高到低排列。"""


def call_llm(cfg: dict, cands: list[dict]) -> dict:
    llm = cfg["llm"]
    api_key = os.environ.get(llm.get("api_key_env", "DEEPSEEK_API_KEY"), "").strip()
    if not api_key:
        raise RuntimeError("没有配置大模型 API Key（.env 里的 DEEPSEEK_API_KEY）")

    lines = []
    for idx, item in enumerate(cands):
        when = f"{item['published']:%m-%d %H:%M}" if item.get("published") else "时间未知"
        summary = item.get("summary", "")[:320]
        lines.append(f"[{idx}] {item['source']} / {when} / {item['title']}\n    摘要：{summary}")

    user = USER_TEMPLATE.format(
        today=f"{now():%Y-%m-%d} {WEEKDAYS[now().weekday()]}",
        hours=cfg["lookback_hours"],
        count=len(cands),
        max_items=cfg["max_items"],
        candidates="\n".join(lines),
    )

    payload = {
        "model": llm["model"],
        "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                     {"role": "user", "content": user}],
        "temperature": 0.3,
        "response_format": {"type": "json_object"},
    }
    url = llm["base_url"].rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}"}
    last_error = None
    for attempt in range(int(llm.get("retries", 2)) + 1):
        try:
            data = http_json(url, payload, headers, timeout=int(llm.get("timeout_seconds", 180)))
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            log(f"大模型返回：prompt={usage.get('prompt_tokens')} completion={usage.get('completion_tokens')} 字符数={len(content)}")
            return json.loads(_strip_fence(content))
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            log(f"大模型调用失败（第 {attempt + 1} 次）：{type(exc).__name__}: {exc}")
            time.sleep(2 + attempt * 3)
    raise RuntimeError(f"大模型调用失败：{last_error}")


def _strip_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        text = text[start:end + 1]
    return text


def select_with_llm(cfg: dict, cands: list[dict]) -> tuple[str, list[dict]]:
    data = call_llm(cfg, cands)
    digest = (data.get("digest") or "").strip()
    picked, used = [], set()
    for entry in data.get("items", []):
        try:
            idx = int(entry["idx"])
        except Exception:
            continue
        if idx < 0 or idx >= len(cands) or idx in used:
            continue
        used.add(idx)
        item = dict(cands[idx])
        item["zh_title"] = (entry.get("title") or item["title"]).strip()
        item["zh_summary"] = (entry.get("summary") or "").strip()
        item["tag"] = (entry.get("tag") or "").strip()
        item["event"] = (entry.get("event") or "").strip()
        item["score"] = int(entry.get("score") or 0)
        picked.append(item)
    picked = [p for p in picked if p["score"] >= cfg["min_score"]]
    picked.sort(key=lambda p: p["score"], reverse=True)
    picked = _dedupe_events(picked)
    picked = _diversify(picked, cfg["max_per_source"])[: cfg["max_items"]]
    return digest, picked


def _event_key(item: dict) -> str:
    event = re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", (item.get("event") or "").lower())
    if event:
        return "event:" + event
    # 没给 event 时，用中文标题的二字组指纹兜底
    title = re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", (item.get("zh_title") or item["title"]).lower())
    return "title:" + title


def _dedupe_events(items: list[dict]) -> list[dict]:
    """同一事件只保留分数最高的一条。"""
    seen: set[str] = set()
    out = []
    for item in items:
        key = _event_key(item)
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def select_with_rules(cfg: dict, cands: list[dict]) -> tuple[str, list[dict]]:
    """没有大模型时的兜底：信源等级 + 时效 + 关键词。"""
    hot = {
        "launch": 2, "release": 2, "announce": 1, "open source": 2, "open-source": 2,
        "model": 1.5, "benchmark": 1, "raise": 1.5, "funding": 1.5, "acquisition": 2,
        "partner": 1, "regulation": 1.5, "gpu": 1, "chip": 1, "agent": 1, "reasoning": 1,
    }
    picked = []
    for item in cands:
        score = 6.0 + (2.0 if item.get("tier") == "T1" else 0.0)
        published = item.get("published")
        if published:
            hours = (now() - published).total_seconds() / 3600
            score += max(0.0, 2.0 - hours / 12)
        blob = (item["title"] + " " + item.get("summary", "")).lower()
        score += min(2.0, sum(w for k, w in hot.items() if k in blob))
        candidate = dict(item)
        candidate["score"] = int(min(10, round(score)))
        candidate["zh_title"] = item["title"]
        candidate["zh_summary"] = (item.get("summary") or "")[:140]
        candidate["tag"] = ""
        picked.append(candidate)
    picked.sort(key=lambda p: (p["score"], p.get("published") or datetime.min.replace(tzinfo=TZ)), reverse=True)
    picked = _diversify(picked, cfg["max_per_source"])[: cfg["max_items"]]
    return "今天值得关注的 AI 动态，按信源等级与热度粗排（本次未启用大模型）。", picked


def _diversify(items: list[dict], per_source: int) -> list[dict]:
    counts: dict[str, int] = {}
    out = []
    for item in items:
        src = item["source"]
        if counts.get(src, 0) >= per_source:
            continue
        counts[src] = counts.get(src, 0) + 1
        out.append(item)
    return out


# --------------------------------------------------------------------------- 飞书

def feishu_token(cfg: dict) -> str:
    conf = cfg["feishu"]
    app_id = os.environ.get(conf["app_id_env"], "").strip()
    secret = os.environ.get(conf["app_secret_env"], "").strip()
    if not app_id or not secret:
        raise RuntimeError(".env 缺少 FEISHU_APP_ID / FEISHU_APP_SECRET")
    data = http_json("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
                     {"app_id": app_id, "app_secret": secret}, timeout=30)
    if data.get("code") != 0:
        raise RuntimeError(f"获取 tenant_access_token 失败：{data.get('code')} {data.get('msg')}")
    return data["tenant_access_token"]


def list_chats(cfg: dict) -> list[dict]:
    token = feishu_token(cfg)
    chats, page_token = [], None
    while True:
        url = "https://open.feishu.cn/open-apis/im/v1/chats?page_size=50"
        if page_token:
            url += f"&page_token={urllib.parse.quote(page_token)}"
        data = http_json(url, headers={"Authorization": f"Bearer {token}"}, timeout=30)
        if data.get("code") != 0:
            raise RuntimeError(f"列出群失败：{data.get('code')} {data.get('msg')}")
        chats.extend(data.get("data", {}).get("items", []) or [])
        page_token = data.get("data", {}).get("page_token")
        if not data.get("data", {}).get("has_more") or not page_token:
            break
    return chats


def send_card(cfg: dict, card: dict) -> dict:
    conf = cfg["feishu"]
    receive_id = os.environ.get(conf["receive_id_env"], "").strip()
    if not receive_id:
        raise RuntimeError(".env 缺少 FEISHU_RECEIVE_ID（群 chat_id，可用 --list-chats 查）")
    token = feishu_token(cfg)
    url = ("https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type="
           + conf.get("receive_id_type", "chat_id"))
    payload = {
        "receive_id": receive_id,
        "msg_type": "interactive",
        "content": json.dumps(card, ensure_ascii=False),
    }
    data = http_json(url, payload, headers={"Authorization": f"Bearer {token}"}, timeout=30)
    if data.get("code") != 0:
        raise RuntimeError(f"发送失败：{data.get('code')} {data.get('msg')} {json.dumps(data)[:400]}")
    return data


def build_card(cfg: dict, digest: str, items: list[dict], stats: dict) -> dict:
    today = now()
    header_title = f"{cfg.get('site_name', '电商 HOT')} {cfg.get('edition', '早报')} · {today:%m月%d日} {WEEKDAYS[today.weekday()]}"

    elements: list[dict] = []
    if digest:
        elements.append({"tag": "markdown", "content": f"**{digest}**"})
    elements.append({
        "tag": "markdown",
        "content": (f"<font color='grey'>{len(items)} 条精选 · 扫描 {stats.get('candidates', 0)} 条 · "
                    f"{stats.get('ok', 0)}/{stats.get('sources', 0)} 个信源在线</font>"),
    })
    elements.append({"tag": "hr"})

    for i, item in enumerate(items, 1):
        when = rel_time(item["published"]) if item.get("published") else "时间未知"
        meta = " · ".join(x for x in [item["source"], when, item.get("tag") or ""] if x)
        title = item.get("zh_title") or item["title"]
        summary = item.get("zh_summary") or ""
        block = f"**{i}. [{_escape_md(title)}]({item['url']})**"
        if summary:
            block += f"\n{summary}"
        block += f"\n<font color='grey'>{_escape_md(meta)}</font>"
        elements.append({"tag": "markdown", "content": block})
        if i != len(items):
            elements.append({"tag": "hr"})

    elements.append({
        "tag": "note",
        "elements": [{"tag": "plain_text",
                      "content": f"电商 HOT × DSH · 每天早上 9:00 自动送达 · 由 徐梓芸的生活管家（DSH）推送"}],
    })

    return {
        "config": {"wide_screen_mode": True, "enable_forward": True},
        "header": {"template": "blue", "title": {"tag": "plain_text", "content": header_title}},
        "elements": elements,
    }


def _escape_md(text: str) -> str:
    return text.replace("[", "［").replace("]", "］")


def sample_card() -> dict:
    return {
        "config": {"wide_screen_mode": True},
        "header": {"template": "blue", "title": {"tag": "plain_text", "content": "电商 HOT 早报 · 链路测试"}},
        "elements": [
            {"tag": "markdown", "content": "**这条是测试消息（电商版）**：飞书机器人「徐梓芸的生活管家（DSH）」已经接通，明天早上 9:00 起会收到正式的 AI 热点早报。"},
            {"tag": "hr"},
            {"tag": "markdown", "content": "**1. [示例] 一条新闻标题会显示成这样**\n摘要会放在标题下面，先给结论，再给关键事实，控制在 60-110 字。\n<font color='grey'>OpenAI · 3 小时前 · 模型</font>"},
            {"tag": "note", "elements": [{"tag": "plain_text", "content": "电商 HOT × DSH"}]},
        ],
    }


# --------------------------------------------------------------------------- 主流程

def main() -> int:
    parser = argparse.ArgumentParser(description="电商 HOT 每日早报 → 飞书")
    parser.add_argument("--config", default=str(ROOT / "config.json"))
    parser.add_argument("--dry-run", action="store_true", help="不推送，只把卡片写到 state/card-preview.json")
    parser.add_argument("--no-llm", action="store_true", help="不调用大模型，用规则排序")
    parser.add_argument("--test", action="store_true", help="发送测试卡片")
    parser.add_argument("--resend", action="store_true", help="重发最近一期卡片（state/card-preview.json）")
    parser.add_argument("--list-chats", action="store_true", help="列出机器人所在的群")
    parser.add_argument("--limit", type=int, default=0, help="临时覆盖条数")
    args = parser.parse_args()

    load_env(ROOT / ".env")
    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    if args.limit:
        cfg["max_items"] = args.limit

    log("=" * 60)
    log(f"电商 HOT 开始运行（{'dry-run' if args.dry_run else '正式'}）")

    if args.list_chats:
        chats = list_chats(cfg)
        if not chats:
            log("机器人不在任何群里。请在飞书建一个群，把这个机器人加进去，再跑一次。")
            return 1
        for chat in chats:
            log(f"chat_id={chat.get('chat_id')} | 名称={chat.get('name')} | 类型={chat.get('chat_type')}")
        return 0

    if args.test:
        send_card(cfg, sample_card())
        log("测试卡片已发送，去飞书看看。")
        return 0

    lock = ROOT / "state" / "run.lock"
    lock.parent.mkdir(exist_ok=True)
    if lock.exists() and (time.time() - lock.stat().st_mtime) < 2700:
        log(f"上一次运行还没结束（{int(time.time() - lock.stat().st_mtime)} 秒前开始），本次跳过。")
        return 0
    lock.write_text(str(os.getpid()), encoding="utf-8")
    try:
        return run_once(cfg, args)
    finally:
        lock.unlink(missing_ok=True)


def run_once(cfg: dict, args) -> int:
    if args.resend:
        preview = ROOT / "state" / "card-preview.json"
        if not preview.exists():
            log("没有可重发的卡片（state/card-preview.json 不存在）")
            return 1
        send_card(cfg, json.loads(preview.read_text(encoding="utf-8")))
        log("已重发最近一期卡片。")
        return 0

    cands, stats = collect(cfg)
    log(f"抓取完成：{stats['ok']}/{stats['sources']} 个信源正常，原始 {stats['raw_items']} 条，去重筛选后 {len(cands)} 条候选")
    for failure in stats["failed"]:
        log(f"  信源异常：{failure}")
    if not cands:
        log("没有新候选，本次不推送。")
        return 0

    if args.no_llm or not os.environ.get(cfg["llm"].get("api_key_env", "DEEPSEEK_API_KEY"), "").strip():
        log("未配置大模型 Key 或指定了 --no-llm，使用规则排序兜底")
        digest, picked = select_with_rules(cfg, cands)
    else:
        try:
            digest, picked = select_with_llm(cfg, cands)
        except Exception as exc:  # noqa: BLE001
            log(f"大模型精选失败，回退规则排序：{exc}")
            digest, picked = select_with_rules(cfg, cands)

    log(f"精选出 {len(picked)} 条")
    for item in picked:
        log(f"  [{item['score']}] {item.get('zh_title') or item['title']} —— {item['source']}")

    card = build_card(cfg, digest, picked, stats)
    preview = ROOT / "state" / "card-preview.json"
    preview.parent.mkdir(exist_ok=True)
    preview.write_text(json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8")

    if not picked:
        log("没有达到入选门槛的内容，本次不推送。")
        return 0

    if args.dry_run:
        log(f"dry-run：卡片已写到 {preview}，未推送。")
        return 0

    send_card(cfg, card)
    save_state(cands)
    log(f"推送成功：{len(picked)} 条 → {cfg['feishu']['receive_id_type']}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        log(f"运行失败：{type(exc).__name__}: {exc}")
        sys.exit(1)
