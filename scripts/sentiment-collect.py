#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sentiment-collect v1.0: 舆情监控数据采集工具
==================================================
基于 OpenProbe investigate-v7.py 改造。
数据源（按优先级）：
  1. baidu-search (百度千帆AI Search) -- 主力搜索引擎
  2. baidu-baike-data (百度百科) -- 结构化品牌信息
  3. web_fetch (直接抓取URL) -- 补充数据源

用法:
  python3 sentiment-collect.py "品牌名" --query "关键词"
  python3 sentiment-collect.py "品牌名" --query "q1" "q2" "q3"
  python3 sentiment-collect.py "品牌名" --query-file queries.txt
  python3 sentiment-collect.py "品牌名" --baike
  python3 sentiment-collect.py "品牌名" --fetch-url "https://..."
  python3 sentiment-collect.py "品牌名" --query "q1" --baike --fetch-file urls.txt

输出: data/{品牌}/raw/*.txt
"""

import argparse, json, os, sys, time, threading, subprocess
from datetime import datetime
from pathlib import Path

# ======================== 配置 ========================
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
WORKSPACE_SKILLS = SKILL_DIR.parent

BAIDU_API_KEY = os.environ.get("BAIDU_API_KEY", "")
BAIDU_SCRIPT = WORKSPACE_SKILLS / "baidu-search" / "scripts" / "search.py"
BAIDU_BAIKE_SCRIPT = WORKSPACE_SKILLS / "baidu-baike-data" / "scripts" / "baidu_baike.py"
DATA_DIR_TEMPLATE = SKILL_DIR / "data"

# 全局并发控制
MAX_CONCURRENT = 2          # 所有请求最大并发数
BAIDU_INTERVAL = 2.5        # 百度搜索最小间隔(秒)
FETCH_INTERVAL = 5.0        # web_fetch 最小间隔(秒)


# ======================== 日志 ========================
def log(msg, level="INFO"):
    tag = {"INFO": "[INFO]", "OK": "[OK]",
           "WARN": "[WARN]", "ERR": "[ERR]"}.get(level, level)
    print("%s %s" % (tag, msg))


def save_raw(data_dir, filename, content):
    """保存原始数据到 data/{品牌}/raw/"""
    out = data_dir / "raw" / filename
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")
    log("  Saved: %s (%d chars)" % (out.name, len(content)))


# ==================== 全局请求队列 ====================
class RequestQueue:
    """
    全局请求队列 -- 所有数据源请求必须通过此队列。
    并发 <= MAX_CONCURRENT，百度额外限速。
    支持三种请求类型: search / baike / fetch
    """

    def __init__(self):
        self.results = {}
        self.errors = {}
        self._semaphore = threading.Semaphore(MAX_CONCURRENT)
        self._lock = threading.Lock()
        self._last_baidu = 0
        self._last_fetch = 0

    def submit_search(self, label, query, data_dir, filename, count=10):
        t = threading.Thread(target=self._do_search,
                             args=(label, query, data_dir, filename, count))
        t.daemon = True
        t.start()

    def submit_baike(self, brand, data_dir):
        t = threading.Thread(target=self._do_baike,
                             args=(brand, data_dir))
        t.daemon = True
        t.start()

    def submit_fetch(self, label, url, data_dir, filename):
        t = threading.Thread(target=self._do_fetch,
                             args=(label, url, data_dir, filename))
        t.daemon = True
        t.start()

    # ---- 限速 ----

    def _wait_baidu(self):
        with self._lock:
            elapsed = time.time() - self._last_baidu
            if elapsed < BAIDU_INTERVAL:
                wait = BAIDU_INTERVAL - elapsed + 0.1
                time.sleep(wait)
            self._last_baidu = time.time()

    def _wait_fetch(self):
        with self._lock:
            elapsed = time.time() - self._last_fetch
            if elapsed < FETCH_INTERVAL:
                time.sleep(FETCH_INTERVAL - elapsed + 0.1)
            self._last_fetch = time.time()

    # ---- 搜索执行 ----

    def _do_search(self, label, query, data_dir, filename, count):
        self._semaphore.acquire()
        try:
            self._wait_baidu()
            results = _search_baidu(query, count)
            content = RequestQueue._format_search_results(label, query, results)
            save_raw(data_dir, filename, content)
            self.results[label] = results
            log("  OK [search:%s]: %d results" % (label, len(results)), "OK")
        except Exception as e:
            log("[search:%s] Error: %s" % (label, e), "ERR")
            self.errors[label] = str(e)
        finally:
            self._semaphore.release()

    def _do_baike(self, brand, data_dir):
        self._semaphore.acquire()
        try:
            self._wait_baidu()
            data = _search_baike(brand)
            if data:
                content = _format_baike_data(data)
                save_raw(data_dir, "baike.txt", content)
                self.results["baike"] = data
                title = data.get("lemma_title", brand)
                log("  OK [baike]: %s" % title, "OK")
            else:
                log("  [baike]: No result for '%s'" % brand, "WARN")
        except Exception as e:
            log("[baike] Error: %s" % e, "ERR")
            self.errors["baike"] = str(e)
        finally:
            self._semaphore.release()

    def _do_fetch(self, label, url, data_dir, filename):
        self._semaphore.acquire()
        try:
            self._wait_fetch()
            result = _web_fetch(url)
            content = "===== %s =====\nURL: %s\nStatus: %s\nLength: %d chars\n---\n%s" % (
                label, url, result.get("status", "?"),
                len(result.get("text", "")), result.get("text", "")
            )
            save_raw(data_dir, filename, content)
            self.results[label] = result
            status = result.get("status", 0)
            ok = 200 <= status < 300
            log("  OK [fetch:%s]: HTTP %d (%d chars)" % (label, status, len(result.get("text", ""))), "OK" if ok else "WARN")
        except Exception as e:
            log("[fetch:%s] Error: %s" % (label, e), "ERR")
            self.errors[label] = str(e)
        finally:
            self._semaphore.release()

    @staticmethod
    def _format_search_results(label, query, results):
        lines = [
            "===== %s =====" % label,
            "Query: %s" % query,
            "Engine: baidu-ai-search",
            "Results: %d" % len(results),
            "---",
        ]
        for i, r in enumerate(results, 1):
            lines.append("")
            lines.append("%d. %s" % (i, r.get("title", "")))
            if r.get("url"):
                lines.append("   URL: %s" % r["url"])
            if r.get("snippet"):
                lines.append("   Snip: %s" % r["snippet"][:300])
        return "\n".join(lines)

    def wait_all(self, timeout=600):
        start = time.time()
        while threading.active_count() > 1:
            if time.time() - start > timeout:
                log("Queue timeout after %ds" % timeout, "ERR")
                break
            time.sleep(0.2)


# ==================== 数据源实现 ====================

def _search_baidu(query, count=10):
    """百度千帆 AI Search"""
    if not BAIDU_API_KEY or not BAIDU_SCRIPT.exists():
        log("Baidu search unavailable (no API key or script)", "WARN")
        return []
    body = json.dumps({"query": query, "count": min(count, 50)}, ensure_ascii=False)
    try:
        env = dict(os.environ)
        env["BAIDU_API_KEY"] = BAIDU_API_KEY
        result = subprocess.run(
            ["python3", str(BAIDU_SCRIPT), body],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True, timeout=25, env=env
        )
        lines = result.stdout.strip().split('\n')
        js_idx = None
        for i, l in enumerate(lines):
            if l.startswith('[') or l.startswith('{'):
                js_idx = i
                break
        if js_idx is None:
            return []
        data = json.loads('\n'.join(lines[js_idx:]))
        items = data if isinstance(data, list) else [data] if isinstance(data, dict) else []
        return [{"title": r.get("title", ""), "url": r.get("url", ""),
                 "snippet": str(r.get("content", ""))[:300], "source": "baidu"}
                for r in items if isinstance(r, dict)]
    except subprocess.TimeoutExpired:
        log("Baidu search timeout (>25s)", "ERR")
        return []
    except Exception as e:
        log("Baidu search fail: %s" % e, "ERR")
        return []


def _search_baike(brand):
    """百度百科结构化查询"""
    if not BAIDU_API_KEY or not BAIDU_BAIKE_SCRIPT.exists():
        log("Baike unavailable (no API key or script)", "WARN")
        return {}
    try:
        env = dict(os.environ)
        env["BAIDU_API_KEY"] = BAIDU_API_KEY
        result = subprocess.run(
            ["python3", str(BAIDU_BAIKE_SCRIPT),
             "--search_type", "lemmaTitle",
             "--search_key", brand],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True, timeout=20, env=env
        )
        text = result.stdout.strip()
        if not text:
            return {}
        if text.startswith('{') or text.startswith('['):
            return json.loads(text)
        return {"raw_text": text, "brand": brand}
    except subprocess.TimeoutExpired:
        log("Baike timeout (>20s)", "ERR")
        return {}
    except Exception as e:
        log("Baike fail: %s" % e, "ERR")
        return {}


def _format_baike_data(baike_data):
    if isinstance(baike_data, dict):
        lines = []
        if baike_data.get("lemma_title"):
            lines.append("Title: %s" % baike_data["lemma_title"])
        if baike_data.get("lemma_desc"):
            lines.append("Desc: %s" % baike_data["lemma_desc"])
        if baike_data.get("url"):
            lines.append("URL: %s" % baike_data["url"])
        abstract = baike_data.get("abstract_plain") or baike_data.get("lemma_abstract")
        if abstract:
            lines.append("\nAbstract:\n%s" % abstract)
        card = baike_data.get("card")
        if card and isinstance(card, list):
            lines.append("\nInfo Card:")
            for item in card:
                name = item.get("name", "")
                value = item.get("value", [])
                if isinstance(value, list):
                    value = ", ".join(str(v) for v in value)
                if name and value:
                    lines.append("  %s: %s" % (name, value))
        return "\n".join(lines)
    return str(baike_data)


def _web_fetch(url, max_chars=8000):
    """直接抓取URL内容"""
    try:
        import urllib.request as ur
        req = ur.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })
        with ur.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        import re
        text = re.sub(r'<script[^>]*>.*?</script>', '', raw, flags=re.S | re.I)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.S | re.I)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        if len(text) > max_chars:
            text = text[:max_chars] + "... [truncated]"
        return {"status": resp.status, "text": text, "url": url}
    except Exception as e:
        return {"status": 0, "text": "ERROR: %s" % e, "url": url}


# ==================== Main ====================
def main():
    p = argparse.ArgumentParser(description="Sentiment Monitor Data Collection v1.0")
    p.add_argument("brand", help="目标品牌名称")

    p.add_argument("--query", nargs="+", metavar="QUERY", help="百度搜索关键词（可多个）")
    p.add_argument("--query-file", type=str, metavar="FILE",
                   help="从文件读取查询列表（每行一个query或 label|query），#开头为注释")

    p.add_argument("--baike", action="store_true", help="查询百度百科")

    p.add_argument("--fetch-url", nargs="+", metavar="URL", help="直接抓取URL（可多个）")
    p.add_argument("--fetch-file", type=str, metavar="FILE",
                   help="从文件读取URL列表（每行一个URL或 label|url），#开头为注释")

    p.add_argument("--round", type=int, default=0, metavar="N",
                   help="轮次编号（自动加文件名前缀防止覆盖，如 --round 1 -> r1_q01.txt）")
    p.add_argument("--data-dir", type=str, help="自定义数据输出目录")

    args = p.parse_args()

    brand = args.brand
    round_prefix = "r%d_" % args.round if args.round > 0 else ""
    data_dir = Path(args.data_dir) if args.data_dir else DATA_DIR_TEMPLATE / brand
    data_dir.mkdir(parents=True, exist_ok=True)

    Q = RequestQueue()
    task_count = 0

    def _fname(label):
        """给文件名加轮次前缀，防止覆盖"""
        return "%s%s.txt" % (round_prefix, label)

    # 搜索任务
    if args.query:
        for i, q in enumerate(args.query):
            label = "q%02d" % (i + 1)
            log("[Q] %s: %s" % (label, q))
            Q.submit_search(label, q, data_dir, _fname(label))
            task_count += 1

    if args.query_file:
        qf = Path(args.query_file)
        if qf.exists():
            for line in qf.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "|" in line:
                    label, query = line.split("|", 1)
                    label, query = label.strip(), query.strip()
                else:
                    label = "q%02d" % task_count
                    query = line
                log("[Q] %s: %s" % (label, query))
                Q.submit_search(label, query, data_dir, _fname(label))
                task_count += 1

    # 百科任务（只查一次，不加轮次前缀）
    if args.baike:
        log("[Q] baike: %s" % brand)
        Q.submit_baike(brand, data_dir)
        task_count += 1

    # URL抓取任务
    if args.fetch_url:
        for i, url in enumerate(args.fetch_url):
            label = "u%02d" % (i + 1)
            log("[Q] %s: %s" % (label, url[:80]))
            Q.submit_fetch(label, url, data_dir, _fname(label))
            task_count += 1

    if args.fetch_file:
        uf = Path(args.fetch_file)
        if uf.exists():
            for line in uf.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "|" in line:
                    label, url = line.split("|", 1)
                    label, url = label.strip(), url.strip()
                else:
                    label = "u%02d" % task_count
                    url = line
                log("[Q] %s: %s" % (label, url[:80]))
                Q.submit_fetch(label, url, data_dir, _fname(label))
                task_count += 1

    if task_count == 0:
        log("No tasks specified.")
        log("Usage: python3 sentiment-collect.py BRAND --query q1 q2 [--baike] [--fetch-url URL]")
        return

    print("\n" + "=" * 60)
    print("  Sentiment Collect v1.0 | Data Collection")
    print("  Target: %s" % brand)
    print("  Tasks: %d | Output: %s/raw/" % (task_count, data_dir))
    print("  Time: %s" % datetime.now().strftime('%Y-%m-%d %H:%M'))
    print("=" * 60 + "\n")

    Q.wait_all()

    # 统计
    rc = len(list((data_dir / "raw").glob("*.txt")))
    ok = len(Q.results.keys())
    err = len(Q.errors.keys())
    print("\n" + "=" * 60)
    print("DONE! Files: %d | OK: %d | Errors: %d" % (rc, ok, err))
    if Q.errors:
        for k, v in Q.errors.items():
            log("  FAIL %s: %s" % (k, v), "ERR")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
