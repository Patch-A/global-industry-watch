# -*- coding: utf-8 -*-
"""生成静态网页 - 读取 articles.json 输出 index.html"""

import json
import os
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "docs")

os.makedirs(OUTPUT_DIR, exist_ok=True)

def load_articles():
    path = os.path.join(DATA_DIR, "articles.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("articles", []), data.get("updated_at", "")
    except (FileNotFoundError, json.JSONDecodeError):
        return [], ""

def generate_html(articles, updated_at):
    articles_json = json.dumps(articles, ensure_ascii=False)

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>全球工业制造业动态 | Global Industrial Manufacturing Watch</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif; background: #f5f6f8; color: #1a1a2e; line-height: 1.6; }}
.header {{ background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%); color: white; padding: 32px 20px; text-align: center; }}
.header h1 {{ font-size: 1.8rem; margin-bottom: 6px; letter-spacing: 1px; }}
.header .subtitle {{ font-size: 0.95rem; opacity: 0.85; }}
.header .updated {{ font-size: 0.8rem; opacity: 0.6; margin-top: 8px; }}
.container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}

/* 搜索栏 */
.search-bar {{ background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); margin-bottom: 20px; display: flex; gap: 12px; flex-wrap: wrap; }}
.search-bar input {{ flex: 1; min-width: 200px; padding: 10px 16px; border: 2px solid #e0e0e0; border-radius: 8px; font-size: 0.95rem; outline: none; transition: border-color 0.2s; }}
.search-bar input:focus {{ border-color: #2c5364; }}
.search-bar select {{ padding: 10px 14px; border: 2px solid #e0e0e0; border-radius: 8px; font-size: 0.9rem; background: white; cursor: pointer; }}
.stats {{ font-size: 0.85rem; color: #666; padding: 4px 0; }}

/* 国家筛选卡片 */
.country-tabs {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 20px; }}
.country-tab {{ padding: 8px 16px; border-radius: 20px; border: 1.5px solid #d0d0d0; background: white; cursor: pointer; font-size: 0.85rem; transition: all 0.2s; white-space: nowrap; user-select: none; }}
.country-tab:hover {{ border-color: #2c5364; color: #2c5364; }}
.country-tab.active {{ background: #2c5364; color: white; border-color: #2c5364; }}

/* 区域分组标题 */
.region-header {{ font-size: 1.1rem; font-weight: 700; color: #444; margin: 24px 0 12px; padding-bottom: 6px; border-bottom: 2px solid #e0e0e0; display: flex; align-items: center; gap: 8px; }}
.region-header .count {{ font-size: 0.8rem; font-weight: 400; color: #888; background: #eee; padding: 2px 10px; border-radius: 10px; }}

/* 新闻卡片 */
.article-card {{ background: white; border-radius: 12px; padding: 20px 24px; margin-bottom: 14px; box-shadow: 0 1px 4px rgba(0,0,0,0.05); border-left: 4px solid #2c5364; transition: transform 0.15s, box-shadow 0.15s; }}
.article-card:hover {{ transform: translateY(-2px); box-shadow: 0 4px 16px rgba(0,0,0,0.1); }}
.article-card.policy {{ border-left-color: #e74c3c; }}
.article-card.tariff {{ border-left-color: #e67e22; }}
.article-card.industry {{ border-left-color: #2c5364; }}
.article-card.smart_mfg {{ border-left-color: #8e44ad; }}
.article-card.building_materials {{ border-left-color: #27ae60; }}
.article-card.ev {{ border-left-color: #2980b9; }}

.card-header {{ display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }}
.card-country {{ font-size: 0.8rem; padding: 3px 10px; border-radius: 12px; background: #e8f4f8; color: #2c5364; font-weight: 600; white-space: nowrap; }}
.card-date {{ font-size: 0.78rem; color: #999; white-space: nowrap; }}
.card-title-cn {{ font-size: 1.05rem; font-weight: 700; color: #1a1a2e; margin-bottom: 4px; line-height: 1.5; }}
.card-title-en {{ font-size: 0.9rem; color: #555; margin-bottom: 10px; font-style: italic; }}
.card-summary {{ font-size: 0.9rem; color: #444; margin-bottom: 10px; line-height: 1.7; }}
.card-summary-en {{ font-size: 0.85rem; color: #777; margin-bottom: 10px; line-height: 1.6; border-left: 3px solid #eee; padding-left: 12px; }}

.card-footer {{ display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }}
.tags {{ display: flex; flex-wrap: wrap; gap: 6px; }}
.tag {{ font-size: 0.75rem; padding: 2px 8px; border-radius: 4px; background: #f0f0f0; color: #666; }}
.source-link {{ font-size: 0.8rem; color: #2c5364; text-decoration: none; font-weight: 500; }}
.source-link:hover {{ text-decoration: underline; }}

.empty-state {{ text-align: center; padding: 60px 20px; color: #999; }}
.empty-state .icon {{ font-size: 3rem; margin-bottom: 12px; }}
.footer {{ text-align: center; padding: 30px; color: #aaa; font-size: 0.8rem; }}

@media (max-width: 640px) {{
  .header h1 {{ font-size: 1.3rem; }}
  .article-card {{ padding: 14px 16px; }}
  .country-tab {{ padding: 6px 12px; font-size: 0.8rem; }}
}}
</style>
</head>
<body>

<div class="header">
  <h1>🌍 全球工业制造业动态</h1>
  <div class="subtitle">Global Industrial Manufacturing Watch — 中国工业企业出海情报</div>
  <div class="updated" id="updateTime">最后更新: {updated_at}</div>
</div>

<div class="container">
  <!-- 搜索栏 -->
  <div class="search-bar">
    <input type="text" id="searchInput" placeholder="搜索标题、摘要、国家、标签...  Search by keyword..." oninput="render()">
    <select id="regionFilter" onchange="render()">
      <option value="all">🌏 全部区域 All Regions</option>
      <option value="Southeast Asia">🇸🇪 东南亚 Southeast Asia</option>
      <option value="Middle East">🇸🇦 中东 Middle East</option>
      <option value="South Asia">🇮🇳 南亚 South Asia</option>
      <option value="Central Asia">🇰🇿 中亚 Central Asia</option>
      <option value="Latin America">🇧🇷 拉美 Latin America</option>
      <option value="Europe">🇪🇺 欧洲 Europe</option>
      <option value="Africa">🇳🇬 非洲 Africa</option>
      <option value="Global">🌐 全球 Global</option>
    </select>
    <select id="categoryFilter" onchange="render()">
      <option value="all">📋 全部分类 All Categories</option>
      <option value="policy">政策法规 Policy</option>
      <option value="tariff">关税变动 Tariff</option>
      <option value="industry">工业制造 Industry</option>
      <option value="smart_mfg">智能制造 Smart Mfg</option>
      <option value="building_materials">建材 Building Materials</option>
      <option value="ev">新能源汽车 EV</option>
    </select>
  </div>

  <!-- 国家快捷筛选 -->
  <div class="country-tabs" id="countryTabs"></div>
  <div class="stats" id="statsBar"></div>

  <!-- 新闻列表 -->
  <div id="articleList"></div>

  <div class="empty-state" id="emptyState" style="display:none;">
    <div class="icon">📭</div>
    <p>暂无匹配的资讯 / No matching articles</p>
  </div>
</div>

<div class="footer">
  <p>数据来源: Google News RSS | AI 摘要: DeepSeek | 自动更新: 每1-2天</p>
  <p>© 2026 Global Industrial Manufacturing Watch</p>
</div>

<script>
const ALL_ARTICLES = {articles_json};

let activeCountry = "all";

function getUniqueCountries() {{
  const countries = [...new Set(ALL_ARTICLES.map(a => a.country))];
  return countries.sort();
}}

function renderCountryTabs() {{
  const countries = getUniqueCountries();
  const tabs = document.getElementById("countryTabs");
  tabs.innerHTML = '<span class="country-tab active" onclick="setCountry(\'all\')">🌍 全部 All</span>';
  countries.forEach(c => {{
    const cls = activeCountry === c ? "country-tab active" : "country-tab";
    tabs.innerHTML += `<span class="${{cls}}" onclick="setCountry('${{c}}')">${{c}}</span>`;
  }});
}}

function setCountry(c) {{
  activeCountry = c;
  renderCountryTabs();
  render();
}}

function formatDate(raw) {{
  if (!raw) return "";
  try {{
    const d = new Date(raw);
    if (isNaN(d.getTime())) return raw;
    return d.toLocaleDateString("zh-CN", {{ year:"numeric", month:"2-digit", day:"2-digit", hour:"2-digit", minute:"2-digit" }});
  }} catch(e) {{ return raw; }}
}}

function render() {{
  const searchTerm = document.getElementById("searchInput").value.toLowerCase();
  const regionFilter = document.getElementById("regionFilter").value;
  const categoryFilter = document.getElementById("categoryFilter").value;

  let filtered = ALL_ARTICLES;

  if (activeCountry !== "all") {{
    filtered = filtered.filter(a => a.country === activeCountry);
  }}
  if (regionFilter !== "all") {{
    filtered = filtered.filter(a => a.region === regionFilter);
  }}
  if (categoryFilter !== "all") {{
    filtered = filtered.filter(a => a.category === categoryFilter);
  }}
  if (searchTerm) {{
    filtered = filtered.filter(a => {{
      const haystack = [
        a.title_cn, a.title_en, a.title_orig,
        a.summary_cn, a.summary_en,
        a.country, a.region,
        ...(a.tags || [])
      ].join(" ").toLowerCase();
      return haystack.includes(searchTerm);
    }});
  }}

  const container = document.getElementById("articleList");
  const empty = document.getElementById("emptyState");
  const stats = document.getElementById("statsBar");

  stats.textContent = `共 ${{filtered.length}} 条资讯 / ${{filtered.length}} articles`;

  if (filtered.length === 0) {{
    container.innerHTML = "";
    empty.style.display = "block";
    return;
  }}

  empty.style.display = "none";

  // 按区域分组
  const regionOrder = ["Southeast Asia", "Middle East", "South Asia", "Central Asia", "Latin America", "Europe", "Africa", "Global"];
  const grouped = {{}};
  filtered.forEach(a => {{
    const r = a.region || "Global";
    if (!grouped[r]) grouped[r] = [];
    grouped[r].push(a);
  }});

  let html = "";
  regionOrder.forEach(r => {{
    if (!grouped[r] || grouped[r].length === 0) return;
    html += `<div class="region-header">${{r}} <span class="count">${{grouped[r].length}} 条</span></div>`;
    grouped[r].forEach(a => {{
      const catClass = a.category || "industry";
      const tagsHtml = (a.tags || []).map(t => `<span class="tag">${{t}}</span>`).join("");
      const dateStr = formatDate(a.fetched_at || a.published_raw);
      html += `
      <div class="article-card ${{catClass}}">
        <div class="card-header">
          <span class="card-country">${{a.country}}</span>
          <span class="card-date">${{dateStr}}</span>
        </div>
        <div class="card-title-cn">${{a.title_cn || a.title_orig}}</div>
        <div class="card-title-en">${{a.title_en || ""}}</div>
        <div class="card-summary">${{a.summary_cn || ""}}</div>
        <div class="card-summary-en">${{a.summary_en || ""}}</div>
        <div class="card-footer">
          <div class="tags">${{tagsHtml}}</div>
          <a class="source-link" href="${{a.link}}" target="_blank" rel="noopener">📎 原文来源 ${{a.source_domain}}</a>
        </div>
      </div>`;
    }});
  }});

  container.innerHTML = html;
}}

// 初始渲染
renderCountryTabs();
render();
</script>
</body>
</html>'''
    return html


def main():
    articles, updated_at = load_articles()
    print(f"加载 {len(articles)} 篇文章，更新时间: {updated_at}")

    html = generate_html(articles, updated_at)
    output_path = os.path.join(OUTPUT_DIR, "index.html")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[DONE] 网页已生成: {output_path}")


if __name__ == "__main__":
    main()
