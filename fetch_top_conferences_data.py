import argparse
import os
import requests
import json
import pandas as pd
import numpy as np

# 支持的会议
SUPPORTED_CONFERENCES = {"iclr", "icml", "neurips"}

def main():
    parser = argparse.ArgumentParser(description="Download and process conference poster/oral data.")
    parser.add_argument("--conference", type=str, required=True, help="Conference name: iclr, icml, neurips")
    parser.add_argument("--year", type=str, required=True, help="Year, e.g., 2025")
    parser.add_argument("--save_dir", type=str, default=".", help="Directory to save files")
    args = parser.parse_args()

    conference = args.conference.lower()
    year = args.year
    save_dir = args.save_dir

    if conference not in SUPPORTED_CONFERENCES:
        raise ValueError(f"Currently only support: {', '.join(SUPPORTED_CONFERENCES)}")

    os.makedirs(save_dir, exist_ok=True)
    json_file = f"{conference}-{year}-orals-posters"
    url = f"https://{conference}.cc/static/virtual/data/{json_file}.json"
    output_file = os.path.join(save_dir, f"{json_file}.json")
    csv_file = os.path.join(save_dir, f"{json_file}.csv")

    # 下载json
    print(f"Downloading from {url}")
    try:
        response = requests.get(url)
        response.raise_for_status()
    except Exception as e:
        print(f"下载失败: {e}")
        return
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(response.text)
    print(f"Downloaded and saved to {output_file}")

    # 读取并处理数据
    with open(output_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if not data.get('results'):
        print("数据文件中 results 为空，程序终止。")
        return
    records = []
    for item in data['results']:
        record = {
            'abstract': item.get('abstract'),
            'authors': ', '.join([a.get('fullname', '') for a in item.get('authors', [])]),
            'decision': item.get('decision').lower() if item.get('decision') else None,
            'name': item.get('name'),
            'paper_url': item.get('paper_url'),
            'topic': item.get('topic'),
        }
        records.append(record)
    df = pd.DataFrame(records)

    # 检查每列的空值数量
    print("\n--- 每列空值数量 ---")
    print(df.isnull().sum())
    # 统计topic和decision的类别及数量
    print("\n--- topic 类别统计 ---")
    print(df['topic'].value_counts(dropna=False))
    print("\n--- decision 类别统计 ---")
    print(df['decision'].value_counts(dropna=False))

    # 优先保留topic不为None的行
    df_sorted = df.copy()
    df_sorted['topic_is_not_none'] = df_sorted['topic'].notnull()
    df_sorted = df_sorted.sort_values(by=['name', 'authors', 'topic_is_not_none'], ascending=[True, True, False])
    df = df_sorted.drop_duplicates(subset=['name', 'authors'], keep='first').drop(columns=['topic_is_not_none'])
    print("\n--- 去重后DataFrame 预览 ---")
    print(df.head())

    # 保存DataFrame为CSV文件
    df.to_csv(csv_file, index=False)
    print(f"\nDataFrame 已保存为 {csv_file}")

    # 随机打印几条topic为None的数据的name
    topic_none_df = df[df['topic'].isnull()]
    print("\n--- 随机抽取 topic 为 None 的 name ---")
    if not topic_none_df.empty:
        print(topic_none_df['name'].sample(n=min(5, len(topic_none_df)), random_state=42).to_list())
    else:
        print("无 topic 为 None 的数据")

if __name__ == "__main__":
    main()