# -*- coding: utf-8 -*-
"""全球工业制造业动态监控系统 - 仅基于真实RSS来源抓取与规则标注"""

import json
import os
import re
import sys
import time
import hashlib
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse

import feedparser
import requests

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
MAX_ARTICLES_PER_FEED = 8
MAX_TOTAL_ARTICLES = 80
CACHE_DAYS = 7
TZ_BEIJING = timezone(timedelta(hours=8))

os.makedirs(DATA_DIR, exist_ok=True)


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
    priorities = authority_config.get("priority_domains", {})
    for level_key in sorted(priorities.keys()):
        for domain_pattern in priorities[level_key]:
            if domain_pattern in domain:
                return int(level_key[0])
    return 5




DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
DEEPSEEK_BASE_URL = 'https://api.deepseek.com/v1'

def call_deepseek(messages, max_tokens=800):
    if not DEEPSEEK_API_KEY:
        return None
    try:
        resp = requests.post(DEEPSEEK_BASE_URL + '/chat/completions',
            headers={'Authorization': 'Bearer ' + DEEPSEEK_API_KEY, 'Content-Type': 'application/json'},
            json={'model': 'deepseek-chat', 'messages': messages, 'max_tokens': max_tokens, 'temperature': 0.3},
            timeout=90)
        resp.raise_for_status()
        return resp.json()['choices'][0]['message']['content']
    except Exception as e:
        print('  [API FAIL] ' + str(e)[:80])
        return None

def translate_article(article):
    orig_lang = article['lang_orig']
    title = article['title_orig'][:300]
    summary = article['summary_raw'][:400]
    is_cn = orig_lang == 'zh'
    is_pt = orig_lang == 'pt'

    if is_cn:
        sys_msg = 'You are a professional translator. Translate Chinese industrial news to English. Output ONLY valid JSON. Do not fabricate.'
        prompt = 'Translate to English. JSON: {"title_en":"English title","summary_en":"English summary"}\nTitle: ' + title + '\nSummary: ' + summary
    elif is_pt:
        sys_msg = 'You are a professional translator. Translate Portuguese industrial news to Chinese AND English. Output ONLY valid JSON. Do not fabricate.'
        prompt = 'Translate to Chinese and English. JSON: {"title_cn":"Chinese title","title_en":"English title","summary_cn":"Chinese summary","summary_en":"English summary"}\nTitle: ' + title + '\nSummary: ' + summary
    else:
        sys_msg = 'You are a professional translator. Translate industrial news to Chinese ONLY. Output ONLY valid JSON. Do not fabricate.'
        prompt = 'Translate to Chinese. JSON: {"title_cn":"Chinese title","summary_cn":"Chinese summary"}\nTitle: ' + title + '\nSummary: ' + summary

    result = call_deepseek([
        {'role': 'system', 'content': sys_msg},
        {'role': 'user', 'content': prompt}
    ], max_tokens=600)
    if result:
        try:
            m = re.search(r'\{[\s\S]*\}', result)
            if m:
                return json.loads(m.group())
        except:
            pass
    return None

COUNTRY_CN = {
    'Vietnam': 'Vietnam', 'Thailand': 'Thailand', 'Indonesia': 'Indonesia',
    'Malaysia': 'Malaysia', 'Philippines': 'Philippines',
    'Saudi Arabia': 'Saudi Arabia', 'UAE': 'UAE', 'Turkey': 'Turkey',
    'India': 'India', 'Bangladesh': 'Bangladesh', 'Pakistan': 'Pakistan',
    'Kazakhstan': 'Kazakhstan', 'Uzbekistan': 'Uzbekistan',
    'Brazil': 'Brazil', 'Mexico': 'Mexico', 'Argentina': 'Argentina',
    'Germany': 'Germany', 'Hungary': 'Hungary', 'Poland': 'Poland',
    'Nigeria': 'Nigeria', 'Egypt': 'Egypt', 'Kenya': 'Kenya',
    'South Africa': 'South Africa', 'Ethiopia': 'Ethiopia',
    'China': 'China', 'Global': 'Global', 'Russia': 'Russia',
    'Japan': 'Japan', 'South Korea': 'South Korea', 'US': 'US',
}

def add_country_cn(article):
    en = article.get('country', '')
    article['country_cn'] = COUNTRY_CN.get(en, en)
    return article

def fetch_rss_feeds(sources_path):
    config = load_json(sources_path)
    feeds = config.get("feeds", [])
    authority_config = config.get("source_authority", {})

    all_articles = []
    seen_fingerprints = set()

    print(f"[{now_str()}] 开始抓取 {len(feeds)} 个 RSS 源...")
    for feed_cfg in feeds:
        try:
            resp = requests.get(
                feed_cfg["url"],
                timeout=15,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            resp.raise_for_status()
            parsed = feedparser.parse(resp.content)

            count = 0
            for entry in parsed.entries[:MAX_ARTICLES_PER_FEED]:
                title = entry.get("title", "").strip()
                link = entry.get("link", "").strip()
                if not title or not link:
                    continue

                fp = article_fingerprint(title, link)
                if fp in seen_fingerprints:
                    continue
                seen_fingerprints.add(fp)

                published = entry.get("published", "") or entry.get("updated", "")
                summary_raw = entry.get("summary", "") or entry.get("description", "")
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
                    "tags": [],
                    "fetched_at": now_str(),
                }
                all_articles.append(article)
                count += 1

            print(f"  [OK] {feed_cfg['name']}: {count} 条")
            time.sleep(0.2)
        except Exception as e:
            print(f"  [FAIL] {feed_cfg['name']}: {str(e)[:80]}")

    print(f"[{now_str()}] 抓取完成，共 {len(all_articles)} 条")
    return all_articles


def dedupe_against_cache(articles, cache_path):
    cache = load_json(cache_path, {"articles": [], "fingerprints": []})
    cached_fps = set(cache.get("fingerprints", []))
    cutoff = (datetime.now(TZ_BEIJING) - timedelta(days=CACHE_DAYS)).isoformat()
    cache["articles"] = [a for a in cache.get("articles", []) if a.get("fetched_at", "") > cutoff]
    cache["fingerprints"] = [a["fingerprint"] for a in cache["articles"]]

    new_articles = [a for a in articles if a["fingerprint"] not in cached_fps]
    print(f"[{now_str()}] 去重后: {len(articles)} -> {len(new_articles)}")
    return new_articles


def enrich_priority_tags(article):
    text = " ".join([
        article.get("title_orig", ""),
        article.get("summary_raw", ""),
        article.get("title_cn", ""),
        article.get("summary_cn", ""),
        article.get("title_en", ""),
        article.get("summary_en", ""),
    ]).lower()

    tags = list(article.get("tags", []))

    def add(tag):
        if tag not in tags:
            tags.append(tag)

    tariff_terms = [
        "tariff", "duty", "customs", "import tax", "tax exemption", "tax relief",
        "temporary reduction", "tariff cut", "duty relief", "suspension", "waiver",
        "关税", "减免", "减税", "免税", "暂缓", "降税", "零关税", "税费减免",
    ]
    visa_terms = [
        "visa", "visa free", "visa-free", "visa waiver", "visa facilitation",
        "entry", "travel", "passport", "免签", "签证", "入境便利", "电子签",
    ]
    china_terms = ["中国", "china", "中资", "出海", "海外建厂", "出口退税", "投资便利"]
    local_terms = ["local", "domestic", "本地", "当地", "内资", "本地建厂", "本地化"]

    if any(keyword in text for keyword in tariff_terms + visa_terms):
        add("政策信号")
    if any(keyword in text for keyword in tariff_terms):
        add("关税变动")
        add("重点关注")
    if any(keyword in text for keyword in visa_terms):
        add("免签/签证")
        add("重点关注")
    if any(keyword in text for keyword in ["tax exemption", "tax relief", "temporary reduction", "reducción", "isenção"]):
        add("税费优惠")
    if any(keyword in text for keyword in china_terms):
        add("中国企业出海")
    if any(keyword in text for keyword in local_terms):
        add("本地布局")

    article["tags"] = tags
    article["signal_level"] = 2 if ("关税变动" in tags or "免签/签证" in tags) else 1 if "政策信号" in tags else 0
    article["signal_badge"] = "重点信号" if article["signal_level"] > 0 else "常规资讯"
    return article


def main():
    sources_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sources.json")
    cache_path = os.path.join(DATA_DIR, "cache.json")
    output_path = os.path.join(DATA_DIR, "articles.json")

    articles = fetch_rss_feeds(sources_path)
    if not articles:
        print("未抓取到文章，退出")
        return

    articles = dedupe_against_cache(articles, cache_path)
    if not articles:
        print("无新文章，退出")
        return

    for article in articles:
        article["title_cn"] = article["title_orig"]
        article["title_en"] = article["title_orig"]
        article["summary_cn"] = article["summary_raw"][:200]
        article["summary_en"] = article["summary_raw"][:200]
        enrich_priority_tags(article)

    articles = articles[:MAX_TOTAL_ARTICLES]

    cache = load_json(cache_path, {"articles": [], "fingerprints": []})
    cache["articles"].extend(articles)
    cache["articles"] = [a for a in cache["articles"] if a.get("fetched_at", "") > (datetime.now(TZ_BEIJING) - timedelta(days=CACHE_DAYS)).isoformat()]
    cache["fingerprints"] = [a["fingerprint"] for a in cache["articles"]]
    save_json(cache_path, cache)

    output = {"updated_at": now_str(), "total": len(articles), "articles": articles}
    save_json(output_path, output)
    print(f"[{now_str()}] 完成，输出 {len(articles)} 条 → {output_path}")


if __name__ == "__main__":
    main()
