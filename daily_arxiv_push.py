import requests
import feedparser
from datetime import datetime, timezone
import os

# 配置关键词组合
KEYWORDS = [
    "LLM", "GPT", '"large language model"', '"agent"',
    "chatgpt", "prompt", "fine-tune", "pretrain"
]

# 构造 arXiv API 查询
def fetch_today_llm_papers():
    today_utc = datetime.now(timezone.utc).date()
    query = "+OR+".join(f"all:{kw}" for kw in KEYWORDS)
    url = (
        f"http://export.arxiv.org/api/query?"
        f"search_query={query}&start=0&max_results=50"
        f"&sortBy=submittedDate&sortOrder=descending"
    )

    resp = requests.get(url)
    feed = feedparser.parse(resp.content)

    papers = []
    for entry in feed.entries:
        pub_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).date()
        if pub_date != today_utc:
            continue

        title = " ".join(entry.title.split())
        authors = ", ".join(a.name for a in entry.authors)
        comment = getattr(entry, "arxiv_comment", "无备注")
        summary = entry.summary.strip().replace("\n", " ")
        summary_short = summary[:300] + ("..." if len(summary) > 300 else "")

        papers.append({
            "title": title,
            "authors": authors,
            "comment": comment,
            "summary_short": summary_short,
            "summary_full": summary,
            "link": entry.link
        })

    return papers


# 构造飞书富文本卡片格式
def build_feishu_card(papers):
    if not papers:
        return {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": f"📭 今日（{datetime.now().strftime('%Y-%m-%d')}）无最新 LLM 论文"
                    }
                },
                "elements": []
            }
        }

    elements = []
    for paper in papers:
        content = (
            f"**标题：** {paper['title']}\n"
            f"**作者：** {paper['authors']}\n"
            f"**备注：** {paper['comment']}\n"
            f"**摘要预览：**\n"
            f"```{paper['summary_short']}```\n"
            f"<collapse>\n```{paper['summary_full']}```\n</collapse>\n"
            f"[🔗 查看论文]({paper['link']})"
        )

        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": content
            }
        })

    return {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"📚 今日 LLM / GPT 最新论文（共 {len(papers)} 篇）"
                }
            },
            "elements": elements
        }
    }


# 发送到飞书机器人 Webhook
def send_to_feishu(card_json):
    webhook = os.environ.get("FEISHU_WEBHOOK")
    if not webhook:
        raise ValueError("请设置环境变量 FEISHU_WEBHOOK")

    resp = requests.post(webhook, json=card_json)
    if resp.status_code != 200:
        print("❌ 飞书推送失败:", resp.status_code, resp.text)
    else:
        print("✅ 推送成功，共发送:", len(card_json.get("card", {}).get("elements", [])), "条论文")


def main():
    papers = fetch_today_llm_papers()
    card = build_feishu_card(papers)
    send_to_feishu(card)


if __name__ == "__main__":
    main()
