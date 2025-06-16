import requests
import feedparser
from datetime import datetime, timezone, timedelta
import os

# 配置关键词组合
KEYWORDS = [
    "LLM", '"large language model"', "agent"
]
# 顶会关键词列表
TOP_CONFS = ["ICML", "ACL", "NIPS", "Neurips", "ICLR", "CVPR", "AAAI", "ECCV", "ICCV", "TPAMI"]
# 常见中文姓氏，用于判断第一作者是否可能为中国人
CHINESE_SURNAMES = [
    "Zhao", "Qian", "Sun", "Li", "Zhou", "Wu", "Zheng", "Wang", "Feng", "Chen",
    "Chu", "Wei", "Jiang", "Shen", "Han", "Yang", "Zhu", "Qin", "You", "Xu",
    "He", "Lu", "Shi", "Zhang", "Kong", "Cao", "Yan", "Bai", "Shui", "Dou",
    "Zhang", "Yun", "Su", "Pan", "Ge", "Xi", "Fan", "Peng", "Lang", "Lu",
    "Wei", "Chang", "Ma", "Miao", "Feng", "Hua", "Fang", "Yu", "Ren", "Yuan",
    "Liu", "Xie", "Lei", "He", "Ni", "Tang", "Teng", "Yin", "Luo", "Bi",
    "Hao", "Wu", "An", "Chang", "Le", "Yu", "Shi", "Fu", "Pi", "Bian",
    "Qi", "Kang", "Wu", "Yu", "Yuan", "Bu", "Gu", "Meng", "Ping", "Huang",
    "He", "Mu", "Xiao", "Yin", "Xu", "Du", "Peng", "Shi", "Yun", "Zhong",
    "Luo", "Yan", "Shang", "Luo", "Huang", "Mu", "Xiao", "Yin", "Xu", "You"
]

# 构造 arXiv API 查询
def fetch_yesterday_llm_papers():
    today_utc = datetime.now(timezone.utc).date()
    yesterday_utc = today_utc - timedelta(days=1)

    query = "+OR+".join(f"all:{kw}" for kw in KEYWORDS)
    url = (
        f"http://export.arxiv.org/api/query?"
        f"search_query={query}&start=0&max_results=200"
        f"&sortBy=submittedDate&sortOrder=descending"
    )

    resp = requests.get(url)
    feed = feedparser.parse(resp.content)

    papers = []
    for entry in feed.entries:
        pub_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).date()
        if pub_date != yesterday_utc:
            continue

        title = " ".join(entry.title.split())
        authors = [a.name for a in entry.authors]
        first_author = authors[0] if authors else ""
        authors_str = ", ".join(authors)
        comment = getattr(entry, "arxiv_comment", "无备注")
        summary = entry.summary.strip().replace("\n", " ")
        summary_short = summary[:300] + ("..." if len(summary) > 300 else "")

        papers.append({
            "title": title,
            "authors": authors_str,
            "first_author": first_author,
            "comment": comment,
            "summary_short": summary_short,
            "summary": summary,
            "link": entry.link
        })

    return papers

# 为每篇论文计算优先级分数
def score_paper(paper):
    score = 0
    c = paper['comment'].lower()
    summary = paper['summary']
    # accepted 标记
    if 'accept' in c:
        score += 3
    # 开源代码
    if 'github' in c or 'github' in summary.lower():
        score += 2
    # 顶会
    for conf in TOP_CONFS:
        if conf.lower() in c:
            score += 2
            break
    # 第一作者名字非中国姓氏
    parts = paper['first_author'].split()
    surname = parts[-1] if parts else ''
    if surname not in CHINESE_SURNAMES:
        score += 1
    return score

# 构造飞书富文本卡片格式
def build_feishu_card(papers, date_str):
    total = len(papers)
    # 按分数降序排序，取前10
    ranked = sorted(papers, key=score_paper, reverse=True)[:10]

    header_title = f"📚 昨日 ({date_str}) 共更新 {total} 篇 LLM 论文，优先展示 Top 10"
    elements = []
    for idx, paper in enumerate(ranked, 1):
        content = (
            f"**{idx}. 标题：** {paper['title']}\n"
            f"**作者：** {paper['authors']}\n"
            f"**备注：** {paper['comment']}\n"
            f"**摘要：** {paper['summary_short']}\n"
            f"[🔗 查看原文]({paper['link']})"
        )
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": content}
        })

    card = {
        "msg_type": "interactive",
        "card": {
            "header": {"title": {"tag": "plain_text", "content": header_title}},
            "elements": elements
        }
    }
    return card

# 发送到飞书机器人 Webhook
def send_to_feishu(card_json):
    webhook = os.environ.get("FEISHU_WEBHOOK")
    if not webhook:
        raise ValueError("请设置环境变量 FEISHU_WEBHOOK")

    resp = requests.post(webhook, json=card_json)
    if resp.status_code != 200:
        print("❌ 飞书推送失败:", resp.status_code, resp.text)
    else:
        print(f"✅ 推送成功，展示 Top {len(card_json['card']['elements'])} 篇论文")


def main():
    papers = fetch_yesterday_llm_papers()
    date_str = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
    card = build_feishu_card(papers, date_str)
    send_to_feishu(card)

if __name__ == "__main__":
    main()
