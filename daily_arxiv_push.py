import requests
import feedparser
from datetime import datetime, timezone, timedelta
import os

# 配置关键词组合
KEYWORDS = [
    "LLM", '"large language model"'
]

# 顶会关键词列表
TOP_CONFS = ["ICML", "ACL", "NIPS", "Neurips", "ICLR", "CVPR", "AAAI", "ECCV", "ICCV", "TPAMI"]

# 常见中文姓氏
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


def fetch_llm_papers_by_date(date_utc):
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
        if pub_date != date_utc:
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


def score_paper(paper):
    score = 0
    c = paper['comment'].lower()
    summary = paper['summary']
    if 'accept' in c:
        score += 3
    if 'github' in c or 'github' in summary.lower():
        score += 2
    for conf in TOP_CONFS:
        if conf.lower() in c:
            score += 2
            break
    parts = paper['first_author'].split()
    surname = parts[-1] if parts else ''
    if surname not in CHINESE_SURNAMES:
        score += 1
    return score


def build_feishu_card(papers, date_str):
    if not papers:
        header_title = f"📚 {date_str} 没有匹配的 LLM 论文更新"
        elements = [{
            "tag": "div",
            "text": {"tag": "lark_md", "content": "今日没有论文可展示。"}
        }]
    else:
        total = len(papers)
        ranked = sorted(papers, key=score_paper, reverse=True)[:10]

        header_title = f"📚 {date_str} 共更新 {total} 篇 LLM 论文，优先展示 Top 10"
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


def send_to_feishu(card_json):
    webhook = os.environ.get("FEISHU_WEBHOOK")
    if not webhook:
        raise ValueError("请设置环境变量 FEISHU_WEBHOOK")

    resp = requests.post(webhook, json=card_json)
    if resp.status_code != 200:
        print("❌ 飞书推送失败:", resp.status_code, resp.text)
    else:
        print(f"✅ 飞书推送成功：{card_json['card']['header']['title']['content']}")


def main(target_date_str=None):
    """
    主函数，支持传入日期字符串（格式 YYYY-MM-DD），默认为昨天
    """
    if target_date_str:
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    else:
        target_date = datetime.now(timezone.utc).date() - timedelta(days=1)

    papers = fetch_llm_papers_by_date(target_date)
    card = build_feishu_card(papers, target_date.isoformat())
    send_to_feishu(card)


if __name__ == "__main__":
    main("2025-06-13")  # 可指定日期调试
    # main()  # 默认昨日
