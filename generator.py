# -*- coding: utf-8 -*-
import json, os, sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "docs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

HTML_TEMPLATE = r"""HTML_GOES_HERE"""

def load_articles():
    path = os.path.join(DATA_DIR, "articles.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("articles", []), data.get("updated_at", "")
    except:
        return [], ""

def main():
    articles, updated_at = load_articles()
    articles_json = json.dumps(articles, ensure_ascii=False)
    html = HTML_TEMPLATE.replace("UPDATED_AT", updated_at).replace("ARTICLES_PLACEHOLDER", articles_json)
    out = os.path.join(OUTPUT_DIR, "index.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[DONE] {len(articles)} articles -> {out}")

if __name__ == "__main__":
    main()
