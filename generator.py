import json, os, sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "docs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def main():
    art_path = os.path.join(DATA_DIR, "articles.json")
    try:
        with open(art_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        articles = data.get("articles", [])
        updated_at = data.get("updated_at", "")
    except:
        articles = []
        updated_at = ""

    tmpl_path = os.path.join(DATA_DIR, "template.html")
    with open(tmpl_path, "r", encoding="utf-8") as f:
        html = f.read()

    articles_json = json.dumps(articles, ensure_ascii=False)
    html = html.replace("UPDATED_AT_PLACEHOLDER", updated_at)
    html = html.replace("ARTICLES_PLACEHOLDER", articles_json)

    out = os.path.join(OUTPUT_DIR, "index.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[DONE] {len(articles)} articles -> {out}")

if __name__ == "__main__":
    main()
