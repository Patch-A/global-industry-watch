# -*- coding: utf-8 -*-
"""
全球工业制造业动态监控系统 - 主脚本
功能: 抓取RSS源 → DeepSeek摘要/翻译/去重 → 生成JSON数据 → 输出静态网页
"""

import json
import os
import sys
import time
import hashlib
import re
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


import requests
import feedparser

# ======== 配置区 ========
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
MAX_ARTICLES_PER_FEED = 8
MAX_TOTAL_ARTICLES = 80
CACHE_DAYS = 7  # 缓存7天内的文章用于去重

# 北京时间
TZ_BEIJING = timezone(timedelta(hours=8))

os.makedirs(DATA_DIR, exist_ok=True)


# ======== 工具函数 ========
def now_str():
    return datetime.now(TZ_BEIJING).strftime("%Y-%m-%d %H:%M:%S")


def load_json(path, default=None):
    if default is None:
        default = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def domain_from_url(url):
    try:
        return urlparse(url).netloc.lower().replace("www.", "")
    except Exception:
        return ""


def article_fingerprint(title, url):
    return hashlib.md5(f"{title[:80]}{domain_from_url(url)}".encode()).hexdigest()


def get_authority_score(domain, authority_config):
    """根据域名返回权威性分数 (越低越权威)"""
    priorities = authority_config.get("priority_domains", {})
    for level_key in sorted(priorities.keys()):
        for domain_pattern in priorities[level_key]:
            if domain_pattern in domain:
                return int(level_key[0])  # 1, 2, 3, 4
    return 5  # 一般媒体


# ======== RSS 抓取 ========
def fetch_rss_feeds(sources_path):
    """抓取所有 RSS 源，返回文章列表"""
    config = load_json(sources_path)
    feeds = config.get("feeds", [])
    authority_config = config.get("source_authority", {})

    all_articles = []
    seen_fingerprints = set()

    print(f"[{now_str()}] 开始抓取 {len(feeds)} 个 RSS 源...")

    for feed_cfg in feeds:
        url = feed_cfg["url"]
        try:
            resp = requests.get(url, timeout=10, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            resp.raise_for_status()
            parsed = feedparser.parse(resp.content)

            count = 0
            for entry in parsed.entries[:MAX_ARTICLES_PER_FEED]:
                title = entry.get("title", "").strip()
                link = entry.get("link", "").strip()
                if not title or not link:
                    continue

                # 去重（同批次内）
                fp = article_fingerprint(title, link)
                if fp in seen_fingerprints:
                    continue
                seen_fingerprints.add(fp)

                published = entry.get("published", "") or entry.get("updated", "")
                summary_raw = entry.get("summary", "") or entry.get("description", "")
                # 清理 HTML 标签
                summary_raw = re.sub(r"<[^>]+>", " ", summary_raw)[:500].strip()

                domain = domain_from_url(link)
                authority = get_authority_score(domain, authority_config)

                article = {
                    "fingerprint": fp,
                    "title_orig": title,
                    "link": link,
                    "published_raw": published,
                    "summary_raw": summary_raw,
                    "source_domain": domain,
                    "authority": authority,
                    "feed_id": feed_cfg["id"],
                    "country": feed_cfg.get("country", "Global"),
                    "region": feed_cfg.get("region", "Global"),
                    "category": feed_cfg.get("category", "general"),
                    "lang_orig": feed_cfg.get("lang", "en"),
                    "title_cn": "",
                    "title_en": "",
                    "summary_cn": "",
                    "summary_en": "",
                    "fetched_at": now_str(),
                }
                all_articles.append(article)
                count += 1

            print(f"  [OK] {feed_cfg['name']}: {count} 条")
            time.sleep(0.3)  # 礼貌间隔

        except Exception as e:
            print(f"  [FAIL] {feed_cfg['name']}: {str(e)[:60]}")

    print(f"[{now_str()}] 抓取完成，共 {len(all_articles)} 条新文章")
    return all_articles


# ======== 去重（跨历史缓存） ========
def dedupe_against_cache(articles, cache_path):
    """与历史缓存去重，保留新文章"""
    cache = load_json(cache_path, {"articles": [], "fingerprints": []})
    cached_fps = set(cache.get("fingerprints", []))

    # 清理过期缓存
    cutoff = (datetime.now(TZ_BEIJING) - timedelta(days=CACHE_DAYS)).isoformat()
    cache["articles"] = [a for a in cache.get("articles", [])
                         if a.get("fetched_at", "") > cutoff]
    cache["fingerprints"] = [a["fingerprint"] for a in cache["articles"]]

    new_articles = [a for a in articles if a["fingerprint"] not in cached_fps]
    print(f"[{now_str()}] 去重: {len(articles)} → {len(new_articles)} 条新内容")
    return new_articles


# ======== DeepSeek API 调用 ========
def call_deepseek(messages, max_tokens=1000):
    """调用 DeepSeek Chat API"""
    if not DEEPSEEK_API_KEY:
        print("  [WARN] 未设置 DEEPSEEK_API_KEY，跳过 AI 处理")
        return None

    try:
        resp = requests.post(
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "deepseek-chat",
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.3,
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"  [FAIL] DeepSeek API 错误: {str(e)[:80]}")
        return None


def summarize_and_translate(article):
    """对单篇文章：生成中英双语摘要、翻译标题、打标签"""
    orig_lang = article["lang_orig"]
    title = article["title_orig"]
    summary = article["summary_raw"][:500]

    prompt = f"""你是一个国际工业制造业资讯编辑。请对以下新闻做处理，返回 JSON 格式：

{{
  "title_cn": "中文标题（如果原文已是中文则保留，否则翻译）",
  "title_en": "英文标题（如果原文已是英文则保留，否则翻译）",
  "summary_cn": "中文摘要（2-4句，提炼核心信息，保留关键数据和名称）",
  "summary_en": "English summary (2-4 sentences, keep key data and names)",
  "tags": ["标签1", "标签2", "标签3"],
  "is_relevant": true/false,
  "relevance_reason": "简短说明是否与中国工业出海相关"
}}

标签从以下选择: 政策法规, 关税变动, 海外建厂, 投资并购, 供应链, 智能制造, 工业4.0, 绿色建材, 新能源汽车, 机械设备, 自动化, 光伏储能, 出口退税, 反倾销, 碳关税CBAM, 一带一路, 本地化, 头部企业动态, 行业趋势

如果新闻与中国工业企业出海完全无关（如纯国内消费新闻、娱乐等），is_relevant 设为 false。

原文标题: {title}
原文语言: {orig_lang}
原文摘要: {summary[:300]}

请只返回 JSON，不要多余文字。"""

    result = call_deepseek([
        {"role": "system", "content": "你是一个专业的工业资讯处理助手，只输出合法JSON。"},
        {"role": "user", "content": prompt}
    ], max_tokens=600)

    if result:
        try:
            # 尝试提取 JSON
            json_match = re.search(r"\{[\s\S]*\}", result)
            if json_match:
                data = json.loads(json_match.group())
                return data
        except (json.JSONDecodeError, AttributeError):
            pass
    return None


def dedupe_similar_with_ai(articles):
    """用 AI 对高度相似的标题进行去重，保留权威性最高的"""
    if len(articles) < 2:
        return articles

    # 按标题相似度分组（简单做法：标题前50字符相同度>80%）
    groups = {}
    for a in articles:
        key = hashlib.md5(re.sub(r"[^\w]", "", a["title_orig"][:50].lower()).encode()).hexdigest()[:8]
        if key not in groups:
            groups[key] = []
        groups[key].append(a)

    deduped = []
    for key, group in groups.items():
        if len(group) == 1:
            deduped.append(group[0])
        else:
            # 按权威性排序，保留最好的
            group.sort(key=lambda x: x["authority"])
            deduped.append(group[0])

    print(f"[{now_str()}] AI去重: {len(articles)} → {len(deduped)} 条")
    return deduped


# ======== 主流程 ========
def main():
    sources_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sources.json")
    cache_path = os.path.join(DATA_DIR, "cache.json")
    output_path = os.path.join(DATA_DIR, "articles.json")

    # 1. 抓取
    articles = fetch_rss_feeds(sources_path)

    if not articles:
        print("未抓取到文章，退出")
        return

    # 2. 与历史缓存去重
    articles = dedupe_against_cache(articles, cache_path)

    if not articles:
        print("无新文章，退出")
        return

    # 3. 按权威性去重（短标题相似组）
    articles = dedupe_similar_with_ai(articles)

    # 4. AI 处理（摘要+翻译+相关性筛选）
    if DEEPSEEK_API_KEY:
        print(f"\n[{now_str()}] 开始 DeepSeek AI 处理...")
        processed = []
        for i, article in enumerate(articles):
            print(f"  [{i+1}/{len(articles)}] {article['title_orig'][:60]}...")
            ai_result = summarize_and_translate(article)

            if ai_result and ai_result.get("is_relevant", True):
                article["title_cn"] = ai_result.get("title_cn", article["title_orig"])
                article["title_en"] = ai_result.get("title_en", article["title_orig"])
                article["summary_cn"] = ai_result.get("summary_cn", "")
                article["summary_en"] = ai_result.get("summary_en", "")
                article["tags"] = ai_result.get("tags", [])
                processed.append(article)
            elif ai_result and not ai_result.get("is_relevant", True):
                print(f"    [SKIP] 不相关: {ai_result.get('relevance_reason', '')}")
            else:
                # AI 失败时保留原文
                article["title_cn"] = article["title_orig"]
                article["title_en"] = article["title_orig"]
                article["summary_cn"] = article["summary_raw"][:200]
                article["summary_en"] = article["summary_raw"][:200]
                article["tags"] = []
                processed.append(article)

            time.sleep(0.3)  # API 频率控制

        articles = processed
        print(f"[{now_str()}] AI 处理完成，保留 {len(articles)} 条相关文章")
    else:
        # 无 API Key 时直接保留原文
        for a in articles:
            a["title_cn"] = a["title_orig"]
            a["title_en"] = a["title_orig"]
            a["summary_cn"] = a["summary_raw"][:200]
            a["summary_en"] = a["summary_raw"][:200]
            a["tags"] = []

    # 5. 限制总数
    articles = articles[:MAX_TOTAL_ARTICLES]

    # 6. 更新缓存
    cache = load_json(cache_path, {"articles": [], "fingerprints": []})
    cache["articles"].extend(articles)
    cache["fingerprints"] = [a["fingerprint"] for a in cache["articles"]]
    # 清理过期
    cutoff = (datetime.now(TZ_BEIJING) - timedelta(days=CACHE_DAYS)).isoformat()
    cache["articles"] = [a for a in cache["articles"] if a.get("fetched_at", "") > cutoff]
    cache["fingerprints"] = [a["fingerprint"] for a in cache["articles"]]
    save_json(cache_path, cache)

    # 7. 保存输出
    output = {
        "updated_at": now_str(),
        "total": len(articles),
        "articles": articles,
    }
    save_json(output_path, output)
    print(f"\n[{now_str()}] [DONE] 完成！输出 {len(articles)} 条文章 → {output_path}")


if __name__ == "__main__":
    main()
